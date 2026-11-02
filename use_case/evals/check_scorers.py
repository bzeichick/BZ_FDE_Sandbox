"""Run every scorer against two dumb baselines. No model calls.
Oracle (the golden answer) must score 1.00; echo (the raw email) should score 0.00."""
import json
from pathlib import Path
from harness import SCORERS

HERE = Path(__file__).parent
cases = [json.loads(line) for line in open(HERE / "golden.jsonl")]

systems = {
    "echo":   lambda c: c["input"]["order_text"],   # returns the email itself
    "oracle": lambda c: json.dumps(c["output"]),    # returns the golden answer
    "empty":  lambda c: json.dumps({}),             # valid JSON with nothing filled in
}

for name, system in systems.items():
    print(name)
    for label, scorer in SCORERS.items():
        scores = [scorer(system(c), c) for c in cases]
        if None in scores:
            print(f"  {label:12} not written yet")
            continue
        misses = [i + 1 for i, s in enumerate(scores) if s < 1]
        print(f"  {label:12} {sum(scores) / len(scores):.2f}   golden lines below 1.0: {misses}")