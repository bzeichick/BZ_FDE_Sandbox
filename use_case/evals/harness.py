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
    # Multi-shipment goldens (line 11) leave per-load fields blank on purpose, because one Response can’t hold two loads. One automatic pass; split into one golden per load when the contract supports several shipments.
    if case.get("multi_shipment"):
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
    want = case["output"]                 # the golden answer
    return 1.0 if got.get("needs_human") == want.get("needs_human") else 0.0

SCORERS = {
    "temperature": temperature_match,
    "silent_gaps": no_silent_gaps,
    "needs_human": needs_human_match,
}