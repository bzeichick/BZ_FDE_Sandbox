"""Step 3, agreement half: does the update judge agree with a human? Plumbing; the labels are the human's.

  uv run python use_case/evals/judge_agreement.py                    # update judge vs your update labels
  uv run python use_case/evals/judge_agreement.py --rubric approve   # broad judge vs your 20 hand scores (pass/fail)

Reads your 1/0 labels from use_case/data/update_labels.md (one per hand-scored trace), asks the judge
the same question about the same agent draft, and reports: agreement, the chance floor (what always
guessing the majority label scores), and every disagreement with the judge's reason.
Prints numbers only, no email text, so the output is safe to paste into the README.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT))

from judge_check import JUDGE_MODEL, ask, pick_rubric   # also loads .env
from helpers.config import from_env
from helpers.judge import Judge

LABELS = ROOT / "use_case" / "data" / "update_labels.md"
TRACES = ROOT / "use_case" / "data" / "human_scores.real.jsonl"


def read_labels() -> dict[str, int]:
    """Label = 1 when your two answers match (q1: email is an update? q2: draft calls it one?)."""
    answers, trace = {}, None
    for line in LABELS.read_text().splitlines():
        m = re.match(r"## trace (\S+)", line)
        if m:
            trace = m.group(1)
        m = re.match(r"(q[12])\b[^:]*:\s*(yes|no)\s*$", line.strip(), re.I)
        if m and trace:
            answers.setdefault(trace, {})[m.group(1).lower()] = m.group(2).lower() == "yes"
    return {t: int(a["q1"] == a["q2"]) for t, a in answers.items() if "q1" in a and "q2" in a}


def main() -> None:
    name, rubric = pick_rubric(sys.argv)
    rows = [json.loads(l) for l in open(TRACES)]
    if name == "approve":    # the human labels are your original hand scores: could ops approve it unchanged?
        labels = {str(r["trace"]): int(str(r["pass"]) == "True") for r in rows}
    else:
        labels = read_labels()
    missing = [str(r["trace"]) for r in rows if str(r["trace"]) not in labels]
    if missing:
        sys.exit(f"Answer q1 and q2 (yes/no) for every trace first. Missing: {', '.join(missing)}")

    judge = Judge(from_env(ROOT), rubric=rubric, model=JUDGE_MODEL)
    agree, disagreements = 0, []
    for r in rows:
        draft = r["actual"] if isinstance(r["actual"], str) else json.dumps(r["actual"], ensure_ascii=False)
        score, why = ask(judge, draft, {"input": r["input"]})
        human = labels[str(r["trace"])]
        if int(score >= 0.5) == human:
            agree += 1
        else:
            disagreements.append((r["trace"], human, int(score >= 0.5), why))
        print(".", end="", flush=True)

    n = len(rows)
    ones = sum(labels[str(r["trace"])] for r in rows)
    floor = max(ones, n - ones) / n
    print(f"\n\nrubric: {name}   judge: {JUDGE_MODEL}   traces: {n}   your labels: {ones} ones, {n - ones} zeros")
    print(f"agreement: {agree}/{n} = {agree / n:.2f}   chance floor (always guess the majority): {floor:.2f}")
    print("above the floor" if agree / n > floor else "NOT above the floor: the judge is no better than guessing")
    for trace, human, j, why in disagreements:
        print(f"  trace {trace}: you {human}, judge {j} - judge's reason: {why}")


if __name__ == "__main__":
    main()
