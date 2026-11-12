"""python use_case/evals/run.py: the whole interface. Scores the order endpoint against the goldens.

  uv run python use_case/evals/run.py --baselines-only   # echo/oracle/empty only, no model calls
  uv run python use_case/evals/run.py                    # also the real endpoint (one model call per golden)
  uv run python use_case/evals/run.py --judge            # plus the update judge column (calibrates first)
  uv run python use_case/evals/run.py --save             # save the endpoint run as baseline.json (Step 6)
  uv run python use_case/evals/run.py --compare          # a new endpoint run vs the saved baseline (Weeks 5-8)
"""
import argparse
import os
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
from harness import SCORERS, bootstrap_ci       # your three scorers (use_case/evals/harness.py)

BASELINE = HERE / "baseline.json"
HEADLINE = "needs_human"          # the costliest mistake (duplicate loads); moved here after the Step 7 rehearsal
GATE = True                        # --no-gate turns off the shared after-check (TC5 feedback: measure each side alone)
WATCH = "temperature"             # the top line of failures.md by count (#1, with #3); gated too

CASES = [json.loads(line) for line in open(HERE / "golden.jsonl")]


def endpoint(inp: dict) -> str:
    """The real order endpoint: the same solve() the API route calls. Order in, JSON string out."""
    from schema import Request, solve           # imported here so --baselines-only needs no model setup
    return solve(Request(**inp)).model_dump_json()


def fixture_only(lookup):
    """Eval isolation (TC5): the TMS sandbox is shared, so other test loads can match a golden's refs
    (golden 3's SYNC8PO1 matched one of the production pipeline's own test loads). Keep only the loads
    seeded from tms_fixture.json, so the sandbox behaves like the TMS as of these emails.
    find_existing_loads itself is unchanged: only what the test lets it see."""
    fixture = {load["intake_id"] for load in json.loads((HERE / "tms_fixture.json").read_text())["loads"]}
    ledger = json.loads((ROOT / "use_case" / "data" / "fde_sandbox_ledger.json").read_text())
    allowed = {oid for iid, rec in ledger.items() if iid in fixture for oid in rec["oids"]}
    return lambda value: [oid for oid in lookup(value) if oid in allowed]


def pipeline_endpoint(inp: dict) -> str:
    """Implementation 1 (TC5): the same solve(), with the TMS checks before and after. Needs the TMS settings."""
    from schema import Request
    import tms_client
    from existing_loads import solve_with_lookup
    return solve_with_lookup(Request(**inp), fixture_only(tms_client.lookup), tms_client.extract, gate=GATE).model_dump_json()


def utcp_endpoint(inp: dict) -> str:
    """Implementation 2 (TC5): the model looks loads up itself through the UTCP manifest's tools,
    then the same after-check as the pipeline. Needs the TMS settings."""
    from schema import Request
    import tms_client
    from utcp_tms import solve_with_utcp
    return solve_with_utcp(Request(**inp), fixture_only(tms_client.lookup), tms_client.extract, gate=GATE).model_dump_json()


SYSTEMS = {
    "echo":   lambda inp: inp["order_text"],                                    # returns the email itself
    "oracle": lambda inp: json.dumps(next(c["output"] for c in CASES if c["input"] == inp)),  # the golden answer
    "empty":  lambda inp: "{}",                                                 # valid JSON, nothing filled
}


def escalation_counts(report) -> dict:
    """Missed and false escalations, read from the needs_human scores (TC5 Step 1, rows 1-2).

    needs_human is exact match, so a 0 on a golden that needs a person is a miss, and a 0
    on one that doesn't is a false escalation. A case that raised also scores 0, so it
    counts as a miss when a person was needed: the safe way round."""
    need = [r for r in report.results if CASES[r.index]["output"].get("needs_human")]
    no_need = [r for r in report.results if not CASES[r.index]["output"].get("needs_human")]
    return {
        "missed": [r.index + 1 for r in need if r.scores["needs_human"] < 1],
        "false": [r.index + 1 for r in no_need if r.scores["needs_human"] < 1],
        "need": len(need),
        "no_need": len(no_need),
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
    parser.add_argument("--save", action="store_true",
                        help="save the endpoint run as use_case/evals/baseline.json (the three model-free scorers only)")
    parser.add_argument("--compare", action="store_true",
                        help="compare this endpoint run with the saved baseline.json")
    parser.add_argument("--judge", action="store_true",
                        help="add the update judge (failure #4) as a column; calibrates it first (judge model calls)")
    parser.add_argument("--pipeline", action="store_true",
                        help="run implementation 1 (TC5: TMS checks around solve) as the endpoint")
    parser.add_argument("--utcp", action="store_true",
                        help="run implementation 2 (TC5: UTCP tools + after-check) as the endpoint")
    parser.add_argument("--no-gate", action="store_true",
                        help="with --pipeline or --utcp: turn off the shared after-check, to measure each side alone")
    args = parser.parse_args()
    global GATE
    GATE = not args.no_gate
    if (args.pipeline or args.utcp) and args.save:
        raise SystemExit("don't --save an implementation over the baseline: use --compare")

    systems = dict(SYSTEMS)
    if not args.baselines_only:
        systems["endpoint"] = utcp_endpoint if args.utcp else pipeline_endpoint if args.pipeline else endpoint

    scorers = dict(SCORERS)
    stats = None
    if args.judge:
        scorers["update_judge"], stats = make_update_judge()

    reports = {}
    for name, system in systems.items():
        print(f"running {name} on {len(CASES)} cases...", flush=True)
        meta = {"model": os.getenv("LLM_MODEL"), "goldens": len(CASES)} if name == "endpoint" else None
        reports[name] = hh.run(CASES, system, scorers, name=(("week5-utcp" if args.utcp else "week5-pipeline" if args.pipeline else "week4-baseline")
                                                         + ("-nogate" if args.no_gate else "")) if name == "endpoint" else name, meta=meta)

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

    if "endpoint" in reports:
        rep = reports["endpoint"]
        print(f"\nIntervals (95% bootstrap over {rep.n} goldens, one endpoint run):")
        for label in labels:
            mean, lo, hi = bootstrap_ci([r.scores[label] for r in rep.results])
            tag = "  <- headline" if label == HEADLINE else "  <- watch" if label == WATCH else ""
            print(f"  {label:13} {mean:.2f}  95% CI [{lo:.2f}, {hi:.2f}]{tag}")
        print(f"  one case = {1 / rep.n:.2f} of every column; compare() calls a drop over 0.02 a regression,"
              " so a single case flipping between runs already reads as one.")
        esc = escalation_counts(rep)
        print(f"\nEscalation: missed {len(esc['missed'])} of {esc['need']} that needed a person (lines {esc['missed']});"
              f" escalated wrongly {len(esc['false'])} of {esc['no_need']} (lines {esc['false']})")

    if args.save or args.compare:
        if "endpoint" not in reports:
            raise SystemExit("--save / --compare need the real endpoint (drop --baselines-only)")
        if args.judge:
            raise SystemExit("baseline.json holds the three model-free scorers only: run --save without --judge")
        if args.save:
            hh.save(reports["endpoint"], BASELINE)
            print(f"\nSaved {BASELINE.relative_to(ROOT)}; compare() of the saved file against this run:")
            print(" ", hh.compare(hh.load(BASELINE), reports["endpoint"]))
        else:
            base = hh.load(BASELINE)
            cmp = hh.compare(base, reports["endpoint"])
            print("\ncompare() against the saved baseline:")
            print(" ", cmp)
            # Gate A (TC5 Step 1, row 2): any increase in missed escalations fails the run, whatever the other columns do
            if cmp.comparable:
                was = len(escalation_counts(base)["missed"])
                now = len(escalation_counts(reports["endpoint"])["missed"])
                if now > was:
                    raise SystemExit(f"REGRESSION: missed escalations {was} -> {now} (any increase fails the run)")
                print(f"  missed escalations {was} -> {now}: OK (gate: any increase fails)")


if __name__ == "__main__":
    main()