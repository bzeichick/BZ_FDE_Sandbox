"""find_existing_loads: the loads already in the TMS that an email's refs point to (TC5 capability).

lookup and extract are passed in rather than imported, so the real TMS client, a counting
wrapper (Step 4) or a mock that reads tms_fixture.json (Docker) all plug in the same way."""
import re

from tms_client import TMSError, summarize

# Known ways a sender rewrites a ref: (pattern whose one group is the real ref, where it was seen).
# Data, not logic: a new format is a new row here, not new code.
REF_RULES = [
    (r"^P\d{3}([A-Z0-9]{5,})$", "dock system: P + 3-digit facility + PO (shadow intake, 6 emails 10/27-11/04)"),
]


def candidates(ref: str) -> list[str]:
    """The ref as written, then what each matching rule pulls out of it, without duplicates."""
    ref = ref.strip()
    found = [ref]
    for pattern, _where in REF_RULES:
        m = re.match(pattern, ref.upper())
        if m and m.group(1) not in found:
            found.append(m.group(1))
    return found


def find_existing_loads(refs: list[str], lookup, extract) -> list[dict]:
    """Loads already in the TMS that match any of these refs. lookup(ref) -> oids; extract(oid) -> one record.
    Each match: oid, the ref as the email wrote it, what was looked up, and summarize() of the record.
    An empty list means no match. A TMS failure is NOT caught: it must never look like "no match"."""
    matches, seen = [], set()
    for ref in dict.fromkeys(r for r in refs if r):     # in order, without duplicates or blanks
        for value in candidates(ref):
            for oid in lookup(value):
                if oid in seen:                          # PO and SO on the same load: extract it once
                    continue
                seen.add(oid)
                matches.append({"oid": oid, "matched_ref": ref, "looked_up": value, **summarize(extract(oid))})
    return matches


# Labels a ref follows in real orders ('PO# 58174', 'Our Order: SO061482', 'Purchase_Order(s) | P003...').
# Data, like REF_RULES: a label seen in a new email is a new entry here.
REF_LABELS = ["PO", "P.O.", "SO", "Order", "BOL", "Load", "Purchase_Order(s)", "Appointment ID", "Confirmation"]
_LABELLED = re.compile(r"\b(?:" + "|".join(re.escape(label) for label in REF_LABELS) + r")"
                       r"\s*(?:#|No\.?|Number)?\s*[:|]?\s*#?\s*([A-Z0-9][A-Z0-9-]{3,})", re.I)


def labelled_refs(text: str) -> list[str]:
    """Numbers that follow a ref label in the email, in order, without duplicates.
    At least 3 digits, so a word after a label ('PO Updated') is never taken for a ref."""
    found = [m.group(1).strip("-") for m in _LABELLED.finditer(text)]
    return list(dict.fromkeys(r for r in found if sum(ch.isdigit() for ch in r) >= 3))


def _tms_block(matches: list[dict]) -> str:
    """The ~300-byte summaries as a short block for the model (never the 10 KB records)."""
    lines = [f"- load {m['shipment_id'] or m['oid']} (matched {m['matched_ref']}): status {m['status']}, "
             f"pickup {m['pickup']} from {m['origin_zip']}, delivery {m['delivery']} to {m['dest_zip']}, "
             f"temp {m['temp_min_f']} to {m['temp_max_f']} F, {m['pallets']} pallets, {m['weight_lb']} lb"
             for m in matches]
    return ("\n\nLOADS ALREADY IN THE TMS that this email's reference numbers match:\n" + "\n".join(lines)
            + "\nIf the order is about one of these loads, it is not a new order: set needs_human, name the "
              "load in needs_human_reason, and list what the email changes in changes.")


def _escalate(draft, reason: str):
    """The same draft, sent to a person with this reason."""
    return draft.model_copy(update={"needs_human": True, "needs_human_reason": reason})


TMS_DOWN = "Couldn't check the TMS for an existing load; check before entering."


def after_check(draft, tried: set, matches: list, lookup, extract):
    """The after-check both implementations share (D4): look up the draft's refs that nothing has tried yet,
    and send the order to a person if any load already in the TMS matches, unless the model already did.
    `matches` are loads found before the draft was written. TMSError is not caught: the caller escalates (D5)."""
    after_refs = [r for r in draft.refs if not set(candidates(r)) <= tried]
    later = find_existing_loads(after_refs, lookup, extract)
    known = {m["oid"] for m in matches}
    hits = matches + [m for m in later if m["oid"] not in known]
    if hits and not draft.needs_human:
        m = hits[0]
        return _escalate(draft, f"Matches load {m['shipment_id'] or m['oid']} already in the TMS "
                                f"(ref {m['matched_ref']}); update that load, don't enter a new order.")
    return draft


def solve_with_lookup(request, lookup, extract):
    """Implementation 1, the pipeline: the before-check looks up the email's labelled refs and gives the
    model any matching loads; one model call; the after-check looks up the draft's other refs and sends
    the order to a person on any match. A TMS failure also goes to a person: never treated as no match."""
    from schema import solve                                     # here, so importing this file needs no model setup

    before_refs = labelled_refs(request.order_text)
    try:
        matches = find_existing_loads(before_refs, lookup, extract)
    except TMSError:
        return _escalate(solve(request), TMS_DOWN)

    draft = solve(request, context=_tms_block(matches) if matches else "")

    tried = {c for r in before_refs for c in candidates(r)}         # don't look the same ref up twice
    try:
        return after_check(draft, tried, matches, lookup, extract)
    except TMSError:
        return _escalate(draft, TMS_DOWN)