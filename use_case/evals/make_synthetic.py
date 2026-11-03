"""Step 4: generate labelled failures by breaking correct golden answers in named ways.

  uv run python use_case/evals/make_synthetic.py      # writes use_case/evals/synthetic.jsonl (no model calls)

Each row is one golden with ONE thing broken. The label is free, because we know what we broke.
Modes trace to failures.md; 'expect' names the scorers that should catch it. N1 has no scorer on
purpose: it shows what the harness does not cover.
"""
import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOLDENS = [json.loads(line) for line in open(HERE / "golden.jsonl")]

TWO_SHIPMENTS = "The order covers two separate shipments, so each needs its own entry."
FAKE_UPDATE = "The customer is changing an existing order that is already in the TMS."

# mode -> (failures.md line, scorers expected to catch it, hard?, description)
MODES = {
    "T1": ("#1", ["temperature"], False, "stated setpoint collapsed into a one-number range"),
    "T2": ("#3", ["temperature"], False, "frozen range copied from the form's example text (0 to 10)"),
    "T3": ("#3", ["temperature"], True, "cold end of the range nudged by 2F"),
    "G1": ("#2", ["silent_gaps"], False, "origin zip blanked and not asked"),
    "G2": ("#2", ["silent_gaps"], True, "one needed customer question removed"),
    "H1": ("#4/#5", ["needs_human"], False, "an order that needs a person passed straight through"),
    "H2": ("#5", ["needs_human"], True, "an ordinary order escalated as 'two shipments'"),
    "U1": ("#4", ["needs_human", "update_judge"], False, "an ordinary order called an update"),
    "N1": ("none", [], False, "pallets off by one (no scorer checks pallets)"),
}


def breaks(g: dict):
    """Yield (mode, broken output) for every mode that applies to this golden."""
    o = g["output"]
    one_order = not g.get("not_one_order")
    if o.get("setpoint_source") == "stated" and o.get("setpoint_f") is not None:
        b = copy.deepcopy(o); b["temp_min_f"] = b["temp_max_f"] = o["setpoint_f"]
        if (b["temp_min_f"], b["temp_max_f"]) != (o["temp_min_f"], o["temp_max_f"]):
            yield "T1", b
    if o.get("temp_mode") == "frozen":
        b = copy.deepcopy(o); b["temp_min_f"], b["temp_max_f"] = 0.0, 10.0
        yield "T2", b
    if o.get("temp_min_f") is not None:
        b = copy.deepcopy(o); b["temp_min_f"] = o["temp_min_f"] + 2
        yield "T3", b
    if one_order and (o.get("origin") or {}).get("zip"):
        b = copy.deepcopy(o); b["origin"]["zip"] = None
        b["questions"] = [q for q in b["questions"] if q.get("field") != "origin"]
        yield "G1", b
    if one_order and o.get("questions"):
        b = copy.deepcopy(o); b["questions"] = b["questions"][1:]
        yield "G2", b
    if o.get("needs_human"):
        b = copy.deepcopy(o); b["needs_human"], b["needs_human_reason"] = False, None
        yield "H1", b
    if not o.get("needs_human"):
        b = copy.deepcopy(o); b["needs_human"], b["needs_human_reason"] = True, TWO_SHIPMENTS
        yield "H2", b
        b = copy.deepcopy(o); b["needs_human"], b["needs_human_reason"] = True, FAKE_UPDATE
        yield "U1", b
    if o.get("pallets"):
        b = copy.deepcopy(o); b["pallets"] = o["pallets"] + 1
        yield "N1", b


def main() -> None:
    rows = []
    for line, g in enumerate(GOLDENS, 1):
        for mode, broken in breaks(g):
            failure_line, expect, hard, desc = MODES[mode]
            row = {
                "input": g["input"],
                "output": g["output"],                      # the original, correct answer
                "actual": json.dumps(broken, ensure_ascii=False),   # the broken copy, as the endpoint would return it
                "failure": mode, "failure_line": failure_line, "description": desc,
                "expect": expect, "hard": hard, "source_golden": line,
            }
            if g.get("not_one_order"):
                row["not_one_order"] = g["not_one_order"]   # scorers read golden labels from the case
            rows.append(row)
    with open(HERE / "synthetic.jsonl", "w") as f:
        f.writelines(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    counts = {m: sum(r["failure"] == m for r in rows) for m in MODES}
    print(f"wrote {len(rows)} generated failures from {len(GOLDENS)} goldens:", counts)


if __name__ == "__main__":
    main()
