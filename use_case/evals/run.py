"""python use_case/evals/run.py: the whole interface. Scores the order endpoint against the goldens.

  uv run python use_case/evals/run.py --baselines-only   # echo/oracle/empty only, no model calls
  uv run python use_case/evals/run.py                    # also the real endpoint (13 model calls)
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baselines-only", action="store_true", help="skip the real endpoint (no model calls)")
    args = parser.parse_args()

    systems = dict(SYSTEMS)
    if not args.baselines_only:
        systems["endpoint"] = endpoint

    reports = {}
    for name, system in systems.items():
        print(f"running {name} on {len(CASES)} cases...", flush=True)
        reports[name] = hh.run(CASES, system, SCORERS, name=name)

    # The Step 2 table, ready to paste into the README.
    labels = list(SCORERS)
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


if __name__ == "__main__":
    main()