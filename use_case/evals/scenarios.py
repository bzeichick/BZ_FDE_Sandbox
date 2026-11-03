"""Step 5: three multi-turn scenarios for the order endpoint (plus one contrast), and the state verifier.

The scenarios are Brian's, written in Session 8; the refusal uses the real (redacted) email from golden 15,
because the cleaned-up S8 version passed while the real one failed (failures.md). A CONTRAST scenario holds the
same facts, date and parties without the noise, so the effect of the noise is measured, not assumed.
(The first contrast, ported from S8, had no shipper and today's date, so it escalated for a missing pickup.)

Two checks per conversation:
  - text:  helpers.simulation.text_check (success phrases said, no must_not phrase said). Course plumbing.
  - state: verified(traj), assertions about the drafted record itself. This is the one that counts.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(ROOT / "01_Product_Engineering" / "challenge"))

from helpers.simulation import Scenario

GOLDENS = [json.loads(line) for line in open(HERE / "golden.jsonl")]
REAL_UPDATE = GOLDENS[14]["input"]          # golden 15: the real "PO has been updated" email, redacted
ORDER_DATE = "2026-10-30"

SCENARIOS = [
    Scenario(
        name="must do: complete frozen order",
        capability="extraction",
        goal="Get a complete frozen order drafted correctly",
        opening=("PO# TEST-501. Pick up Acme Cold Storage, 100 Harbor Rd, Vernon CA 90058, ready 11/3. "
                 "Deliver to Sample Foods DC, 200 Main St, Reno NV 89502, by 11/5. "
                 "4 pallets, 320 cases, 7,200 lb. Frozen -10."),
        success=["TEST-501", "Temp: frozen -10"],
        must_not=["NEEDS A PERSON", "Question:"],         # it had everything: no escalation, no questions
    ),
    Scenario(
        name="must ask: temperature withheld",
        capability="asks_for_missing",
        goal="Book an order without saying the temperature unless asked",
        opening=("PO# TEST-502. Pick up Acme Cold Storage, 100 Harbor Rd, Vernon CA 90058, ready 11/3. "
                 "Deliver to Sample Foods DC, 200 Main St, Reno NV 89502. 2 pallets, 160 cases, 3,400 lb."),
        knows={"temperature": "frozen, -10F"},
        success=["TEST-502", "Temp: frozen"],
        must_not=["NEEDS A PERSON"],                       # a missing temperature is a question, not a hand-off
    ),
    Scenario(
        name="must refuse: real update email",
        capability="escalation",
        goal="Change an order that is already booked",
        opening=REAL_UPDATE["order_text"],
        success=["needs a person"],
        must_not=["Question:"],                            # hand it to ops; don't interrogate the customer
    ),
    Scenario(
        name="contrast: cleaned-up update email",
        capability="escalation",
        goal="Change an order that is already booked",
        # The real email's facts, date and parties, minus the noise (signature, dock hours, BOL fine print):
        # so a difference between the two scenarios is the noise, not missing information.
        opening=("From: Carla Navarro <cn@lakeshorefoodservice.example>\n"
                 "Subject: Lakeview PO Updated\n\n"
                 "Lakeview PO has been updated to # 5697090-1\n\n"
                 "--- Attachment: Bill of Lading SH048213.pdf ---\n"
                 "Shipper: LFS Harbor Warehouse, 1420 Harbor Street, Los Angeles CA 90021\n"
                 "Consignee: Lakeview ISD Food Service Deliver Warehouse, 300 Commerce Way, Garland TX 75040\n"
                 "Customer Order: 5697090-1   Our Order: SO061482\n"
                 "Product must remain frozen 0°F or less. Pick up Friday 7/18. Deliver on or before Wednesday 7/23.\n"
                 "480 cases, 6 pallets, 8,640 lb."),
        success=["needs a person"],
        must_not=["Question:"],
    ),
]
REQUIRED = SCENARIOS[:3]          # the three the challenge asks for; SCENARIOS[3] is the contrast
RECEIVED = {SCENARIOS[2].name: REAL_UPDATE["received_date"], SCENARIOS[3].name: REAL_UPDATE["received_date"]}


def _refs(r) -> str:
    return " ".join(r.refs)


# The verifier: assertions about the drafted record (traj.states), never about the words.
# Each line: (what it checks, test on the final draft, test on every draft in the conversation).
VERIFY = {
    "must do: complete frozen order": lambda final, states, traj: (
        "TEST-501" in _refs(final) and final.temp_mode == "frozen" and final.temp_min_f == -10
        and not final.needs_human            # must_not: escalate
        and not final.questions              # must_not: ask about what it was given (the over-asking blind spot)
        and final.rate_usd is None),         # must_not: invent a rate
    "must ask: temperature withheld": lambda final, states, traj: (
        "TEST-502" in _refs(final) and final.temp_mode == "frozen"
        and states[0].temp_mode is None      # must_not: fill a temperature before the customer gave it
        and not any(s.needs_human for s in states)),   # must_not: escalate a missing temperature
    "must refuse: real update email": lambda final, states, traj: (
         bool(states[0].needs_human)          # must_not: draft it as a new order (duplicate load), on the FIRST reply
        and not states[0].questions),        # must_not: interrogate the customer
    "contrast: cleaned-up update email": lambda final, states, traj: (
        bool(states[0].needs_human) and not states[0].questions),
}


def verified(traj) -> float:
    states = getattr(traj, "states", [])
    return float(bool(states) and VERIFY[traj.scenario.name](states[-1], states, traj))


def render_draft(r) -> str:
    """What a reviewer sees (from Session 8): the filled fields, the questions, whether it needs a person."""
    d = r.model_dump(mode="json")
    lines = [f"Refs: {', '.join(d['refs']) or '-'}"]
    for stop in ("origin", "destination"):
        if d.get(stop):
            lines.append(f"{stop.title()}: " + ", ".join(str(v) for v in d[stop].values() if v))
    if d.get("temp_mode"):
        lines.append(f"Temp: {d['temp_mode']} {d.get('temp_min_f')}..{d.get('temp_max_f')}F")
    lines.append(f"Pallets {d.get('pallets')} · weight {d.get('weight_lb')} lb")
    for q in d.get("questions", []):
        lines.append(f"Question: {q['question'] if isinstance(q, dict) else q}")
    if d.get("needs_human"):
        lines.append(f"NEEDS A PERSON: {d.get('needs_human_reason')}")
    return "\n".join(lines)


def order_agent(traj) -> str:
    """The endpoint as agent(traj): the whole thread, newest message first (the Week 4 contract)."""
    from schema import Request, solve
    user_text = [text for who, text in traj.turns if who == "user"]
    thread = "\n\n--- earlier message ---\n".join(reversed(user_text))
    response = solve(Request(order_text=thread, received_date=RECEIVED.get(traj.scenario.name, ORDER_DATE)))
    traj.states = getattr(traj, "states", []) + [response]
    return render_draft(response)
