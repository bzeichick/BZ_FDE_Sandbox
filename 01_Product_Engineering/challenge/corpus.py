"""The corpus, as records: one per TMS shipment, email, or email attachment.

Every retrieval technique in Week 3 reads from load_corpus(), so all three
search exactly the same text and cite exactly the same IDs.

Two sources, picked by an environment variable:
  COLDLADE_DB set   -> production: Broker's orders.db, opened READ-ONLY.
                       Used locally for the measurement. Never committed.
  COLDLADE_DB unset -> the shipped synthetic orders (corpus/synthetic_v1.jsonl),
                       so anyone who clones the repo can run the endpoint.

The unit is the record the data already gives us (one shipment, one email,
one attachment). Nothing is cut inside a record here: README Step 3 says to
start with the record boundary and only chunk further if measured.
"""

import email
import html
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from email import policy
from email.utils import parsedate_to_datetime
from pathlib import Path

SYNTHETIC = Path(__file__).parent / "corpus" / "synthetic_v1.jsonl"


@dataclass
class Record:
    id: str            # what an answer cites: "84477", "msg:16250", "msg:16250#att1", "syn:0012"
    kind: str          # "shipment" | "email" | "attachment" (matches SourceKind in schema.py)
    date: str          # ISO date (YYYY-MM-DD) the record belongs to; used for as_of
    title: str         # one line a person can recognise: subject, or "Shipment 84477 - customer"
    text: str          # the searchable text
    meta: dict = field(default_factory=dict)   # customer, thread id, sender... for filters later


def load_corpus() -> list[Record]:
    """All records, from production if COLDLADE_DB points at orders.db, else synthetic.

    COLDLADE_LIVE_MAIL (optional, production only): ColdLade's coldlade-eval/data folder, where the
    server's weekday mail pull is copied (backfill/ and intake/ .eml files). Adds the business email
    received since the export. Left unset for measure.py, so the measured corpus stays the frozen snapshot."""
    db = os.environ.get("COLDLADE_DB")
    if not db:
        return _load_synthetic(SYNTHETIC)
    records = _load_production(db)
    live = os.environ.get("COLDLADE_LIVE_MAIL")
    if live:
        seen = {r.meta["msgid"] for r in records if r.meta.get("msgid")}
        records += _live_emails(Path(live).expanduser(), seen)
    return records


def as_of(records: list[Record], day: date | None) -> list[Record]:
    """Only the records that existed on `day` (all of them if day is None)."""
    if day is None:
        return records
    cutoff = day.isoformat()
    return [r for r in records if r.date and r.date <= cutoff]


# ---------------------------------------------------------------------------
# Cleaning email text (same rules as ColdLade: agent.py clean(), index_orders.py top_of())
# ---------------------------------------------------------------------------

# Where quoted history starts in a reply or forward. Everything from here down is
# an older message that has its own record already.
QUOTED = re.compile(
    r"\n\s*(?:From:\s|-----\s*Original Message|_{10,}|On .{5,80} wrote:|Sent from my )",
    re.I,
)

# Blocks repeated on every message that say nothing about this order.
BOILERPLATE = [
    r"All shipments must be securely packaged.*?wait time\.",
    r"Confidentiality Notice:.*?(?:in the future\.|$)",
    r"This communication \(including any attachments\).*?strictly prohibited\.",
    r"The contents of this e-mail message.*?privileged\s+information\.",
]


def new_text(body: str) -> str:
    """The part of an email its sender actually wrote: no quoted thread, no legal footer."""
    body = body or ""
    m = QUOTED.search(body)
    if m:
        body = body[: m.start()]
    for pattern in BOILERPLATE:
        body = re.sub(pattern, "", body, flags=re.S | re.I)
    body = re.sub(r"<mailto:[^>]+>|<https?://[^>]+>|<tel:[^>]+>", "", body)
    body = re.sub(r"[ \t]+", " ", body)
    return re.sub(r"\n\s*\n+", "\n", body).strip()


# ---------------------------------------------------------------------------
# Production: orders.db
# ---------------------------------------------------------------------------

def _load_production(db_path: str) -> list[Record]:
    # mode=ro: opened read-only, so nothing here can ever change ColdLade's data.
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    return _shipments(con) + _emails(con) + _attachments(con)


def temp_mode(temp) -> str:
    """The charter's temperature modes from a recorded range (frozen -10 to 0, refrigerated 34 to 38).
    Written into the record text so a search for "refrigerated" or "frozen" can match a range."""
    if not temp:
        return "no temperature on record"
    lo, hi = sorted(temp)
    if hi <= 10:
        return "frozen"
    if lo >= 28 and hi <= 45:
        return "refrigerated"
    return "other range"


# How a freight description names its mode when the temperature field is empty.
MODE_WORDS = [(re.compile(r"^\s*frozen", re.I), "frozen"),
              (re.compile(r"^\s*(chill|refrig|reefer)", re.I), "refrigerated"),
              (re.compile(r"^\s*(dry|ambient|room temp)", re.I), "ambient")]


def temp_from_desc(desc: str | None) -> tuple[list[int] | None, str | None]:
    """(range, mode) read from a freight description: 'Frozen, -10 to 0' -> ([-10, 0], 'frozen'),
    'Refrigerated 38' -> ([38, 38], 'refrigerated'), 'Dry - Genset' -> (None, 'ambient').

    Needed because the rate-confirmation parser only reads one way of writing a range: 303 of the
    363 shipments with an empty temperature field state their temperature in the description."""
    desc = desc or ""
    mode = next((m for rx, m in MODE_WORDS if rx.search(desc)), None)
    if mode in (None, "ambient"):
        return None, mode
    # Whole numbers only: '34-38' is 34 and 38 (not -38), and 'R4324' is a code, not a temperature.
    nums = [int(n) for n in re.findall(r"(?<![\dA-Za-z])-?\d+", desc)][:2]
    if not nums:
        return None, mode
    return sorted(nums) if len(nums) == 2 else [nums[0], nums[0]], mode


def temperature(items: dict) -> tuple[str, list[int] | None, str]:
    """The shipment's temperature as (text for the record, range, mode), from the temperature
    field, or else from the freight description (and the text says which)."""
    t = items.get("temp")
    if t:
        lo, hi = sorted(t)
        return f"{temp_mode(t)}, {lo} to {hi} F", [lo, hi], temp_mode(t)
    rng, mode = temp_from_desc(items.get("desc"))
    if rng:
        return f"{temp_mode(rng)}, {rng[0]} to {rng[1]} F (from the freight description)", rng, temp_mode(rng)
    if mode:
        return f"{mode} (from the freight description; no range given)", None, mode
    return "not on record", None, "no temperature on record"


def _stop(s: dict) -> str:
    place = ", ".join(p for p in (s.get("name"), s.get("street"), s.get("city")) if p)
    when = " ".join(s.get("earliest") or [])
    return f"{place}, {s.get('state') or ''} {s.get('zip') or ''} | {when}".strip()


def _shipments(con) -> list[Record]:
    """One record per TMS shipment (parsed from the carrier rate confirmations)."""
    out = []
    for (data,) in con.execute("SELECT data FROM rc_shipment"):
        d = json.loads(data)
        items = d.get("items") or {}
        temp_text, temp_range, mode = temperature(items)
        pickup, delivery = d.get("pickup") or {}, d.get("delivery") or {}
        text = "\n".join([
            f"Shipment {d['shipment_id']} (Load {d.get('load_id')})",
            f"Customer: {d.get('customer') or ''}",
            f"Customer PO: {d.get('customer_po') or ''}",
            f"Pickup reference: {d.get('pickup_ref') or ''}",
            f"Pickup: {_stop(pickup)}",
            f"Delivery: {_stop(delivery)}",
            f"Delivery appointment: {d.get('delivery_appt') or ''}",
            f"Temperature: {temp_text}",
            f"Freight: {items.get('pallets')} pallets, {items.get('weight_lb')} lb, {items.get('desc') or ''}",
            f"Carrier: {d.get('carrier') or ''} | carrier cost (what we pay, not the customer rate): ${d.get('carrier_total')}",
        ])
        out.append(Record(
            id=d["shipment_id"],
            kind="shipment",
            date=(pickup.get("earliest") or [d.get("doc_date")])[0] or "",
            title=f"Shipment {d['shipment_id']} - {d.get('customer') or 'unknown customer'}",
            text=text,
            meta={"customer": d.get("customer"), "pickup": pickup, "delivery": delivery,
                "temp": temp_range, "mode": mode, "pallets": items.get("pallets")},
        ))
    return out


def _emails(con) -> list[Record]:
    """One record per kept order email, new text only, one copy of each message."""
    out, seen = [], set()
    rows = con.execute(
        "SELECT id, msgid, conv_id, sent, from_addr, from_name, to_addrs, subject, body "
        "FROM msg WHERE keep IN ('rule', 'keyword') ORDER BY id"
    )
    for mid, msgid, conv, sent, frm, frm_name, to, subject, body in rows:
        # The mailbox stores some messages twice (Sent Items + Inbox). Keep the first.
        key = msgid or (frm, sent, subject)
        if key in seen:
            continue
        seen.add(key)
        text = new_text(body)
        if not text:
            continue
        out.append(Record(
            id=f"msg:{mid}",
            kind="email",
            date=(sent or "")[:10],
            title=subject or "(no subject)",
            text=f"Subject: {subject}\nFrom: {frm_name} <{frm}>\nTo: {to}\nSent: {sent}\n\n{text}",
            meta={"thread": conv, "from": frm, "sent": sent, "msgid": (msgid or "").strip("<> ")},
        ))
    return out


def _attachments(con) -> list[Record]:
    """Attachment text (POs, freight and appointment confirmations...), cited as their email.

    Carrier rate confirmations are left out: they are already the shipment records,
    and indexing both would put the same facts under two IDs.
    """
    out, n_by_msg = [], {}
    rows = con.execute(
        "SELECT a.msg_id, a.name, f.text, m.sent, m.subject, f.sha "
        "FROM att a JOIN att_file f USING (sha) JOIN msg m ON m.id = a.msg_id "
        "WHERE m.keep IN ('rule', 'keyword') "
        "AND lower(a.name) NOT LIKE 'carrier_rate_confirmation%' "
        "AND f.text IS NOT NULL AND trim(f.text) != '' "
        "ORDER BY a.msg_id, a.name"
    )
    for mid, name, text, sent, subject, sha in rows:
        n_by_msg[mid] = n_by_msg.get(mid, 0) + 1
        out.append(Record(
            id=f"msg:{mid}#att{n_by_msg[mid]}",
            kind="attachment",
            date=(sent or "")[:10],
            title=f"{name} (attached to: {subject})",
            text=f"Attachment: {name}\nAttached to email: {subject} ({sent})\n\n{text.strip()}",
            meta={"email": f"msg:{mid}", "file": name, "sha": sha},   # same sha = same file
        ))
    return out

# ---------------------------------------------------------------------------
# Live mail: what the server's weekday pull has saved since the export
# ---------------------------------------------------------------------------

def _html_text(s: str) -> str:
    s = re.sub(r"(?is)<(style|script).*?</\1>", "", s)
    s = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>|</li>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def _live_index(root: Path) -> dict[str, dict]:
    """eml file name -> its index entry (received time, conversation id) from the pull's own logs."""
    index = {}
    for log in [root / "backfill" / "index.jsonl", *sorted(root.glob("intake/*/messages.jsonl"))]:
        if log.exists():
            for line in log.read_text().splitlines():
                entry = json.loads(line)
                if entry.get("eml"):
                    index[Path(entry["eml"]).name] = entry
    return index


def _live_emails(root: Path, seen: set[str]) -> list[Record]:
    """Business emails saved by the server's pull (.eml), one per Message-ID, skipping any already
    in orders.db. Body text only for now: attachments in these emails are not read yet."""
    until = os.environ.get("COLDLADE_LIVE_UNTIL")          # snapshot cutoff (measure.py --live); unset in the app
    until = datetime.fromisoformat(until) if until else None
    index, out = _live_index(root), []
    for path in sorted(root.rglob("*.eml")):
        with open(path, "rb") as f:
            msg = email.message_from_binary_file(f, policy=policy.default)
        msgid = (msg.get("Message-ID") or "").strip().strip("<>")
        if msgid in seen:
            continue                      # already in orders.db, or a second copy of the same message
        seen.add(msgid or str(path))
        part = msg.get_body(preferencelist=("plain", "html"))
        body = part.get_content() if part is not None else ""
        if part is not None and part.get_content_type() == "text/html":
            body = _html_text(body)
        text = new_text(body)
        if not text:
            continue
        entry = index.get(path.name, {})
        try:
            sent = parsedate_to_datetime(msg["Date"]).astimezone(timezone.utc)   # UTC, like orders.db's dates
        except (TypeError, ValueError):
            continue
        if until and sent > until:
            continue                      # arrived after the snapshot cutoff
        out.append(Record(
            id=f"eml:{path.parent.name}/{path.stem}",
            kind="email",
            date=sent.date().isoformat(),
            title=str(msg.get("Subject") or "(no subject)"),
            text=f"Subject: {msg.get('Subject') or ''}\nFrom: {msg.get('From') or ''}\nTo: {msg.get('To') or ''}\n"
                 f"Sent: {sent.isoformat(timespec='seconds')}\n\n{text}",
            meta={"thread": entry.get("conversation"), "from": str(msg.get("From") or ""),
                  "sent": sent.isoformat(timespec="seconds"), "msgid": msgid, "live": True},
        ))
    return out


# ---------------------------------------------------------------------------
# Synthetic: the shipped TC2 orders
# ---------------------------------------------------------------------------

def _load_synthetic(path: Path) -> list[Record]:
    out = []
    with open(path) as f:
        for i, line in enumerate(f):
            row = json.loads(line)
            order = row["input"]
            subject = next((l[9:] for l in order["order_text"].splitlines() if l.startswith("Subject: ")), "")
            out.append(Record(
                id=f"syn:{i:04d}",
                kind="email",
                date=order.get("received_date") or "",
                title=subject or f"Synthetic order {i}",
                text=order["order_text"],
            ))
    return out


if __name__ == "__main__":
    # `python corpus.py` prints what's in the corpus: the size numbers Step 3 asks for.
    records = load_corpus()
    by_kind = {}
    for r in records:
        n, chars = by_kind.get(r.kind, (0, 0))
        by_kind[r.kind] = (n + 1, chars + len(r.text))
    total = sum(c for _, c in by_kind.values())
    for kind, (n, chars) in by_kind.items():
        print(f"{kind:11} {n:7,} records  {chars:13,} chars")
    print(f"{'total':11} {len(records):7,} records  {total:13,} chars  (~{total // 4:,} tokens at 4 chars/token, an estimate)")