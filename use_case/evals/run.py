"""python use_case/evals/run.py: the whole interface. Scores the order endpoint against the goldens.

  uv run python use_case/evals/run.py --baselines-only   # echo/oracle/empty only, no model calls
  uv run python use_case/evals/run.py                    # also the real endpoint (one model call per golden)
  uv run python use_case/evals/run.py --judge            # plus the update judge column (calibrates first)
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHALLENGE = ROOT / "01_Product_Engineering" / "challenge"
sys.path.insert(0, str(ROOT))
sys.path.insert(1, str(CHALLENGE))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")                      # LLM_MODEL and API keys, same as the endpoint uses

from helpers import harness as hh               # the course's run/save/load/compare
from harness import SCORERS                     # your three scorers (use_case/evals/harness.py)

CASES = [json.loads(line) for line in open(HERE / "golden.jsonl")]


def endpoint(inp: dict) -> str:
    """The real order endpoint: the same solve() the API route calls. Order in, JSON string out."""
    from schema import Request, solve           # imported here so --baselines-only needs no model setup
    return solve(Request(**inp)).model_dump_json()


SYSTEMS = {
    "echo":   lambda inp: inp["order_text"],                                    # returns the email itself
    "oracle": lambda inp: json.dumps(next(c["output"] for c in CASES if c["input"] == inp)),  # the golden answer
    "empty":  lambda inp: "{}",                                                 # valid JSON, nothing filled
}


def make_update_judge():
    """The update judge as a harness scorer. Calibrates first: helpers.judge refuses to score until it passes."""
    from helpers.config import from_env
    from helpers.judge import Judge
    from helpers.llm import CallStats
    from harness import UPDATE_RUBRIC
    from judge_check import JUDGE_MODEL, judge_case

    stats = CallStats()
    judge = Judge(from_env(ROOT), rubric=UPDATE_RUBRIC, model=JUDGE_MODEL, stats=stats)
    print(f"calibrating update judge ({JUDGE_MODEL}) on {len(CASES)} goldens...", flush=True)
    print(" ", judge.calibrate([judge_case(c) for c in CASES]))      # raises later in score() if this failed
    return (lambda actual, case: judge.score(actual, judge_case(case))), stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baselines-only", action="store_true", help="skip the real endpoint (no model calls)")
    parser.add_argument("--judge", action="store_true",
                        help="add the update judge (failure #4) as a column; calibrates it first (judge model calls)")
    args = parser.parse_args()

    systems = dict(SYSTEMS)
    if not args.baselines_only:
        systems["endpoint"] = endpoint

    scorers = dict(SCORERS)
    stats = None
    if args.judge:
        scorers["update_judge"], stats = make_update_judge()

    reports = {}
    for name, system in systems.items():
        print(f"running {name} on {len(CASES)} cases...", flush=True)
        reports[name] = hh.run(CASES, system, scorers, name=name)

    # The Step 2 table, ready to paste into the README.
    labels = list(scorers)
    print("\n| System | " + " | ".join(labels) + " | errors |")
    print("| --- | " + " | ".join("---" for _ in labels) + " | --- |")
    for name, r in reports.items():
        print(f"| {name} | " + " | ".join(f"{r.means[l]:.2f}" for l in labels) + f" | {r.errors} |")

    if "endpoint" in reports:
        print("\nEndpoint misses (golden line: scorers below 1.0):")
        for res in reports["endpoint"].results:
            failed = [l for l, s in res.scores.items() if s < 1]
            if failed or res.error:
                print(f"  line {res.index + 1}: {', '.join(failed)}" + (f"  ERROR: {res.error.splitlines()[-1]}" if res.error else ""))

    if stats is not None:
        print(f"\nJudge calls this run (measured): {stats}")


if __name__ == "__main__":
    main()