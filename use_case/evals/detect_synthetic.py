"""Step 4: which scorer catches which generated failure? Prints the detection table for the README.

  uv run python use_case/evals/detect_synthetic.py            # the three model-free scorers (free, instant)
  uv run python use_case/evals/detect_synthetic.py --judge    # plus the update judge (calibrates first; judge calls)

A scorer 'catches' a broken copy when it scores it below 1.0. Every row was broken on purpose, so an
uncaught row is a miss by that scorer. Bold = a scorer expected to catch that mode.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from harness import SCORERS

NATURAL = 18          # failures found in the 50 real traces (failures.md, Step 1)
TRACES = 50


def main() -> None:
    rows = [json.loads(line) for line in open(HERE / "synthetic.jsonl")]
    scorers = dict(SCORERS)
    if "--judge" in sys.argv:
        from run import make_update_judge                # calibrates the judge first, as in run.py --judge
        scorers["update_judge"], stats = make_update_judge()
    from make_synthetic import MODES
    modes = [m for m in MODES if any(r["failure"] == m for r in rows)]

    print(f"Natural failures: {NATURAL} of {TRACES} real traces. Generated failures: {len(rows)}.\n")
    print("| Mode | Failure | What was broken | n | " + " | ".join(scorers) + " |")
    print("| --- | --- | --- | --- | " + " | ".join("---" for _ in scorers) + " |")
    for m in modes:
        group = [r for r in rows if r["failure"] == m]
        cells = []
        for name, scorer in scorers.items():
            caught = sum(scorer(r["actual"], r) < 1 for r in group)
            cell = f"{caught}/{len(group)}"
            cells.append(f"**{cell}**" if name in group[0]["expect"] else cell)
        hard = " (hard)" if group[0]["hard"] else ""
        print(f"| {m} | {group[0]['failure_line']} | {group[0]['description']}{hard} | {len(group)} | " + " | ".join(cells) + " |")
    if "--judge" in sys.argv:
        print(f"\nJudge calls (measured): {stats}")


if __name__ == "__main__":
    main()
