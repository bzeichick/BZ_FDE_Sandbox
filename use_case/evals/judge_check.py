"""Step 3: check the update judge before trusting it. Plumbing; the rubric is UPDATE_RUBRIC in harness.py.

  uv run python use_case/evals/judge_check.py

Separation: the judge scores every golden answer (the oracle, should be ~1.0) and three known-bad
outputs (the course's "The answer is 42.", the raw email = echo, and {} = empty; all should be ~0.0).
Every golden the oracle doesn't score 1 is printed with the judge's own reason: those are the
lines to read. The judge is a different model from the endpoint (JUDGE_MODEL, default gpt-4.1-mini).
"""
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from helpers.config import from_env
from helpers.judge import Judge, parse_json
from harness import UPDATE_RUBRIC

JUDGE_MODEL = os.getenv("JUDGE_MODEL", "gpt-4.1-mini")
CASES = [json.loads(line) for line in open(HERE / "golden.jsonl")]


def judge_case(c: dict) -> dict:
    """What the judge sees: the email as plain text (not a dict), and the golden answer as JSON."""
    return {"input": c["input"]["order_text"], "output": json.dumps(c["output"], ensure_ascii=False)}


def ask(judge: Judge, actual: str, case: dict) -> tuple[float, str]:
    """One judgement, with the judge's reason. Unparseable = 0.0, never a pass."""
    reply = judge._ask(judge.rubric.format(input=case["input"], expected="", actual=actual))
    parsed = parse_json(reply) or {}
    try:
        return max(0.0, min(1.0, float(parsed.get("score", 0)))), str(parsed.get("why", reply[:160]))
    except (TypeError, ValueError):
        return 0.0, f"unparseable: {reply[:160]}"


def main() -> None:
    judge = Judge(from_env(ROOT), rubric=UPDATE_RUBRIC, model=JUDGE_MODEL)
    jcases = [judge_case(c) for c in CASES]
    systems = {
        "oracle": lambda jc: jc["output"],
        "answer-42": lambda jc: "The answer is 42.",
        "echo": lambda jc: jc["input"],
        "empty": lambda jc: "{}",
    }
    print(f"judge model: {JUDGE_MODEL}   endpoint model: {os.getenv('LLM_MODEL')}   cases: {len(CASES)}\n")
    means, oracle_misses = {}, []
    for name, system in systems.items():
        scores = []
        for i, jc in enumerate(jcases, 1):
            score, why = ask(judge, system(jc), jc)
            scores.append(score)
            if name == "oracle" and score < 1:
                oracle_misses.append((i, why))
        means[name] = sum(scores) / len(scores)
        print(f"  {name:10} mean {means[name]:.2f}", flush=True)

    bad = max(means["answer-42"], means["echo"], means["empty"])
    print(f"\nseparation (oracle - worst bad): {means['oracle'] - bad:.2f}")
    print("PASS" if means["oracle"] > 0.8 and bad < 0.3 else "FAIL: do not use this judge yet",
          "(course bar: oracle > 0.8, every bad < 0.3)")
    if oracle_misses:
        print("\nGolden lines the oracle did NOT score 1 (read these):")
        for i, why in oracle_misses:
            print(f"  line {i}: {why}")


if __name__ == "__main__":
    main()
