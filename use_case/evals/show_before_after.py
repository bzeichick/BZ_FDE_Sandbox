"""Plain-language before/after of one attack, from the saved replies (for showing a non-technical stakeholder).
    python use_case/evals/show_before_after.py h3"""
import glob
import json
import sys

attack = sys.argv[1] if len(sys.argv) > 1 else "h3"
before = after = None
for f in sorted(glob.glob(f"use_case/data/attack_runs/{attack}/*.json")):
    r = json.load(open(f))
    fin = r.get("final") or {}
    if not r.get("model", "").endswith("16k"):
        continue
    if fin.get("rate_usd") is not None:
        before = fin
    elif "rate_claims" in fin:
        after = fin


def show(label, fin):
    print(f"\n=== {label} ===")
    rate = fin.get("rate_usd")
    print("Price that gets billed:   ", f"${rate:,.2f}" if rate is not None else "(empty: not set by the system)")
    print("Order status:             ", fin.get("order_status"))
    print("Sent to a person?         ", "yes" if fin.get("needs_human") else "no")
    for c in fin.get("rate_claims") or []:
        print("Price claim for approver: ", f"${c.get('amount_usd'):,.2f}", "| stated by:", c.get("stated_by"),
              "| where:", c.get("appeared_in"), "| words:", repr(c.get("words")))


show("BEFORE the fix", before)
show("AFTER the fix", after)