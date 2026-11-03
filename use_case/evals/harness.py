"""Week 4 scorers for the order-entry endpoint. Each one traces to a line in failures.md."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # the repo root
sys.path.insert(0, str(ROOT))
from helpers.judge import parse_json               # finds the JSON object even if wrapped in text


def _parse(actual: str) -> dict | None:
    """The endpoint's reply as a dict, or None if it isn't JSON. Shared plumbing, not a scorer."""
    if isinstance(actual, dict):                     # the oracle may hand us a dict directly
        return actual
    return parse_json(actual)

def _blank(value) -> bool:
    """True for None, an empty string, or an empty list. 0 is NOT blank."""
    return value is None or value == "" or value == []

def pallets_match(actual: str, case: dict) -> float:
    """Example only (not in SCORERS). Pallet count equals the golden's."""
    got = _parse(actual)
    if got is None:                       # not JSON: a failed answer, never a pass
        return 0.0
    want = case["output"]                 # the golden answer
    return 1.0 if got.get("pallets") == want.get("pallets") else 0.0

def temperature_match(actual: str, case: dict) -> float:
    """Temperature range built from a single number: a setpoint like "chilled @ 32" or "frozen at zero degree" entered as 32–32 or 0–0 instead of the mode's standard range"""
    got = _parse(actual)
    if got is None:
        return 0.0
    want = case["output"]
    for field in ["temp_mode", "temp_min_f", "temp_max_f", "setpoint_f"]:                    # check each one in turn
        got_temp = got.get(field)   # "or {}" so an empty field doesn't crash
        want_temp = want.get(field)
        if got_temp != want_temp:                             # the first mismatch fails the whole thing
            return 0.0
    return 1.0                                                # every temperature matched

# Known limit: rewards asking. An agent that asks about every field passes, even fields it filled in.
# Not penalized yet; goes in the Step 6 decision row (Why / What would change your mind).
def no_silent_gaps(actual: str, case: dict) -> float:
    """Required gap left silent: both stop zips missing, neither asked nor flagged (all one customer's trucking form)"""
    got = _parse(actual)
    if got is None:                       # not JSON: a failed answer, never a pass
        return 0.0
    # Not one order goldens emails whose right answer isn’t one new order to enter, because their blanks are deliberate, since there’s no single order to complete.
    if case.get("not_one_order"):
        return 1.0
    asked = {q.get("field") for q in (got.get("questions") or [])}
    for field in ["refs", "temp_mode", "pallets", "pieces", "weight_lb"]:
        if _blank(got.get(field)) and field not in asked:       # blank AND nobody asked
            return 0.0        
    if _blank(got.get("ready_date")) and _blank(got.get("pickup_date")) and "ready_date" not in asked:
        return 0.0    
    for name in ["origin", "destination"]:
        stop = got.get(name) or {}
        incomplete = any(_blank(stop.get(p)) for p in ["company", "street", "city", "state", "zip"])
        if incomplete and name not in asked:
            return 0.0
    return 1.0


def needs_human_match(actual: str, case: dict) -> float:
    """Escalation wrong: once over (two POs ops booked as one load), once under (a "please accept this tender" message that isn't an order)"""
    got = _parse(actual)
    if got is None:                       # not JSON: a failed answer, never a pass
        return 0.0
    want = case["output"]                 # the golden
    return 1.0 if got.get("needs_human") == want.get("needs_human") else 0.0

SCORERS = {
    "temperature": temperature_match,
    "silent_gaps": no_silent_gaps,
    "needs_human": needs_human_match,
}

UPDATE_RUBRIC = """You are checking one draft that was produced from one customer email.

Question: Did the draft correctly decide whether this email is an update to an existing order?

You can only see the email and the draft, not the TMS. Decide from what the email itself says.

Email:
{input}

Draft:
{actual}

What counts as an update. An email is an update when it asks to change an order that already exists: one the customer says was sent, booked or scheduled before this email. Both of these must be true:
1. It asks for a change: wording like "updated", "revised", "please change", "instead of", or a new quantity, date or PO number for something already ordered.
2. It points to a specific existing order: a PO or SO number, a reference like "the order I sent Monday", or "the attached PO going to [consignee] this week".

What does not count as an update:
- A repeat order: a regular customer asking to ship a similar amount of the same product, with no specific earlier order named and no request to change one. That is a new order, even if it looks familiar.
- A change inside this same thread before booking: the customer answers a question or corrects a detail in a reply ("make it 6 pallets instead of 5"). That is still one new order being completed, and the draft records it under `changes`.

How a draft says "update". The draft has no update field. It says the email is an update only when
needs_human is true AND needs_human_reason says the email changes an order that already exists
(for example "the PO on an existing load was updated" or "customer is revising an existing order").
A draft escalated for any other reason (two shipments in one email, a tender, a missing address,
a load already picked up) is NOT calling it an update.

A status report about a load ("picked up", "delivered", "on the way") is not an update, even if it
uses the word "update": it doesn't ask to change anything.

Scoring:
- Score 1 if the draft's decision matches the email: the draft calls it an update and the email is
  one, or the draft does not call it an update and the email is not one, whatever else the draft
  escalates for.
- Score 0 if the decision is wrong in either direction, or if the text is not a draft at all.
  A draft must contain a needs_human field set to true or false. Empty JSON ({{}}), an email,
  or any text without needs_human is not a draft: score 0, even when the email is not an update.
- Judge only this decision. Ignore errors in other fields.

Example of a 1:
Email: "Please change PO 4471 going to Fresh Valley Thursday to 8 pallets instead of 6."
Draft: needs_human true, needs_human_reason "Customer is changing existing PO 4471 to 8 pallets."

Example of a 0:
Email: "Same as usual, 10 pallets of romaine to the Fresno DC next week."
Draft: needs_human true, needs_human_reason "Update to an existing order."
No earlier order is named and nothing is asked to change, so this is a repeat order, not an update.

Reply with JSON only: {{"score": 0 or 1, "why": "<one sentence>"}}"""