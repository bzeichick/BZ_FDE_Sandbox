"""Technique 2's wiki: profile pages generated from the TMS shipment records.

Direct corpus interaction needs named pages with headings and an index. The corpus
has none (flat shipment records, email threads), so this file MAKES them: one page
per customer and one per pickup facility, each with counts and shares at the top
and the shipment IDs behind every number, so a citation resolves to a TMS record.

Pages are computed from the records on demand for a given as_of date (a page is a
saved query result), so they are never stale and never show the future.
This is also the start of ColdLade's customer profiles (today hand-written).
"""

import re
from collections import Counter, defaultdict
from datetime import date

from corpus import Record

DIRECTIONS = {"n", "s", "e", "w", "north", "south", "east", "west"}
SUFFIX = re.compile(r"(road|rd|avenue|ave|boulevard|blvd|street|st|drive|dr|way|parkway|pkwy)$")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or "unknown"


def customer_key(name: str | None) -> str:
    """One key per customer however it was typed: 'Redstone freight' = 'Redstone Freight'."""
    name = re.sub(r"[.,]", "", (name or "").lower())
    name = re.sub(r"\b(inc|llc|co|corp|company)\b", "", name)
    return slug(name)


def facility_key(stop: dict) -> str:
    """One key per building however its address was typed.

    '1800 Alameda Way', '1800 Alameda Way.' and '1800 South Alameda Way' (Los Angeles)
    are one place; so are '4400 Commerce Ave.', '4400 Commerce Blvd.' and '4400 CommerceRoad'.
    Key = house number + main street word (suffix and direction removed) + city.
    """
    words = re.findall(r"[a-z0-9]+", (stop.get("street") or "").lower())
    number = words[0] if words and words[0].isdigit() else ""
    rest = [w for w in words[1:] if w not in DIRECTIONS] if number else words
    core = rest[0] if rest else ""
    if len(core) > 5:
        core = SUFFIX.sub("", core)          # 'commerceroad' -> 'commerce'
    city = re.sub(r"[^a-z]", "", (stop.get("city") or "").lower())[:6]   # 'Los Angele' = 'Los Angeles'
    if not (number or core):
        return slug(f"{stop.get('name') or ''} {city}")
    return slug(f"{number} {core} {city}")


def _temp_text(temp) -> str:
    return f"{min(temp)} to {max(temp)} F" if temp else "no range given"


def _share(n: int, total: int) -> str:
    return f"{n} ({round(100 * n / total)}%)" if total else str(n)


def _ids(rs: list[Record], limit: int = 8) -> str:
    """The shipment IDs behind a number: newest first, so citations are recent and checkable."""
    ids = [r.id for r in sorted(rs, key=lambda r: (r.date, r.id), reverse=True)]
    return ", ".join(ids[:limit]) + (f" (+{len(ids) - limit} more)" if len(ids) > limit else "")


def _place(stop: dict) -> str:
    return ", ".join(p for p in (stop.get("name"), stop.get("street"), stop.get("city"), stop.get("state")) if p)


def build(records: list[Record], as_of: str) -> dict[str, str]:
    """Every page, as {page name: markdown}, from shipments dated on or before as_of."""
    ships = [r for r in records if r.kind == "shipment" and r.date and r.date <= as_of]
    by_customer, by_facility = defaultdict(list), defaultdict(list)
    for r in ships:
        by_customer[customer_key(r.meta.get("customer"))].append(r)
        by_facility[facility_key(r.meta.get("pickup") or {})].append(r)

    def most_common(rs, get):
        return Counter(get(r) for r in rs).most_common(1)[0][0]

    pages, cust_names, fac_names = {}, {}, {}
    for key, rs in by_customer.items():
        cust_names[key] = most_common(rs, lambda r: r.meta.get("customer") or "Unknown customer")
    for key, rs in by_facility.items():
        fac_names[key] = most_common(rs, lambda r: _place(r.meta.get("pickup") or {}) or "Unknown pickup")

    # --- One page per customer ---------------------------------------------------
    for key, rs in by_customer.items():
        n = len(rs)
        lines = [f"# Customer: {cust_names[key]}", "",
                 f"{n} shipments in the TMS, {min(r.date for r in rs)} to {max(r.date for r in rs)} (as of {as_of}).",
                 "Cite the shipment IDs listed here, not this page name.", "", "## Temperature"]
        modes = defaultdict(list)
        for r in rs:
            modes[(r.meta.get("mode"), _temp_text(r.meta.get("temp")))].append(r)
        for (mode, rng), group in sorted(modes.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"- {mode}, {rng}: {_share(len(group), n)} shipments, e.g. {_ids(group, 5)}")
        lines += ["", "## Pickup locations"]
        facs = defaultdict(list)
        for r in rs:
            facs[facility_key(r.meta.get("pickup") or {})].append(r)
        for fkey, group in sorted(facs.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"- {fac_names[fkey]} [page facility:{fkey}]: {_share(len(group), n)} shipments, e.g. {_ids(group, 5)}")
        lines += ["", "## Delivery cities"]
        cities = Counter(", ".join(p for p in ((r.meta.get("delivery") or {}).get("city"), (r.meta.get("delivery") or {}).get("state")) if p) or "unknown" for r in rs)
        lines += [f"- {c}: {_share(k, n)}" for c, k in cities.most_common(10)]
        lines += ["", "## Shipments, newest first", "", "date | shipment | pickup | delivery | temperature | pallets"]
        for r in sorted(rs, key=lambda r: (r.date, r.id), reverse=True):
            p, d = r.meta.get("pickup") or {}, r.meta.get("delivery") or {}
            lines.append(f"{r.date} | {r.id} | {p.get('city') or ''} | {d.get('city') or ''}, {d.get('state') or ''} | "
                         f"{r.meta.get('mode')} {_temp_text(r.meta.get('temp'))} | {r.meta.get('pallets')}")
        pages[f"customer:{key}"] = "\n".join(lines)

    # --- One page per pickup facility ----------------------------------------------
    for fkey, rs in by_facility.items():
        n = len(rs)
        lines = [f"# Pickup facility: {fac_names[fkey]}", "",
                 f"{n} shipments picked up here, {min(r.date for r in rs)} to {max(r.date for r in rs)} (as of {as_of}).",
                 "Addresses typed differently for the same building are counted together:"]
        spellings = Counter(_place(r.meta.get("pickup") or {}) for r in rs)
        lines += [f"- {s}: {k}" for s, k in spellings.most_common()]
        lines += ["", "## Customers who picked up here", "",
                  "customer | shipments | first | latest | latest shipment"]
        custs = defaultdict(list)
        for r in rs:
            custs[customer_key(r.meta.get("customer"))].append(r)
        for ckey, group in sorted(custs.items(), key=lambda kv: max(r.date for r in kv[1]), reverse=True):
            latest = max(group, key=lambda r: (r.date, r.id))
            lines.append(f"{cust_names[ckey]} [page customer:{ckey}] | {len(group)} | {min(r.date for r in group)} | "
                         f"{latest.date} | {latest.id}")
        pages[f"facility:{fkey}"] = "\n".join(lines)

    # --- The index ---------------------------------------------------------------------
    index = [f"# Index (as of {as_of})", "",
             "Pages: customer:<name> and facility:<address>, generated from TMS shipments.",
             "Any record can also be read by its ID (84477, msg:16250, msg:16250#att1).", "",
             "## Customers (by shipments)"]
    index += [f"- customer:{k} -- {cust_names[k]} ({len(rs)})"
              for k, rs in sorted(by_customer.items(), key=lambda kv: -len(kv[1]))]
    index += ["", "## Pickup facilities (by shipments)"]
    index += [f"- facility:{k} -- {fac_names[k]} ({len(rs)})"
              for k, rs in sorted(by_facility.items(), key=lambda kv: -len(kv[1]))]
    pages["index"] = "\n".join(index)
    return pages


_built: dict[str, dict[str, str]] = {}


def pages_for(records: list[Record], as_of: date) -> dict[str, str]:
    """The pages as of a date, built once per date and then reused (well under a second to build)."""
    key = as_of.isoformat()
    if key not in _built:
        _built[key] = build(records, key)
    return _built[key]