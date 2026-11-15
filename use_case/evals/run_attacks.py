"""TC6 Steps 2-3: run the attacks in attacks.jsonl against the LOCAL model, score every reply with leaked().

    uv run python use_case/evals/run_attacks.py                     # new attacks only (no "runs" yet), 3 runs each
    uv run python use_case/evals/run_attacks.py --id h1 --runs 8    # re-run one attack, 8 times
    uv run python use_case/evals/run_attacks.py --all               # re-run every attack
    uv run python use_case/evals/run_attacks.py --id h1 --dry-run   # print the exact email; no model call

Attacks never go to a hosted model. The script switches the app to INJECTION_MODEL itself and
stops unless that model is served from this machine, so .env is never edited and can't be left wrong.
It attacks the plain draft step (schema.solve), not the TMS-checked pipeline: whether a rate was
agreed doesn't depend on the TMS lookup, and no tunnel or TMS credentials are needed.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CHALLENGE = ROOT / "01_Product_Engineering" / "challenge"
ATTACKS = HERE / "attacks.jsonl"
GOLDENS = [json.loads(line) for line in open(HERE / "golden.jsonl")]
RAW_DIR = ROOT / "use_case" / "data" / "attack_runs"   # gitignored: every raw reply, for review and the Step 6 demo
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def use_local_model() -> str:
    """Point the app at INJECTION_MODEL, or stop. Must run before the app's modules are imported,
    because llm.py reads LLM_MODEL once, at import."""
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    model, base = os.getenv("INJECTION_MODEL"), os.getenv("INJECTION_API_BASE")
    if not model or not base:
        sys.exit("INJECTION_MODEL / INJECTION_API_BASE aren't set in .env. Attacks only go to a local model.")
    if urlparse(base).hostname not in LOCAL_HOSTS:
        sys.exit(f"INJECTION_API_BASE is {base}, which isn't this machine. This script only attacks a local model.")
    if "ollama" in model:                                   # fail in 3 s, not after three 60 s timeouts
        try:
            urllib.request.urlopen(base.rstrip("/") + "/api/tags", timeout=3)
        except Exception:
            sys.exit(f"Can't reach Ollama at {base}. Start it (open the Ollama app, or `ollama serve`) and retry.")
    os.environ["LLM_MODEL"], os.environ["LLM_API_BASE"] = model, base
    os.environ.pop("LLM_EXTRA_HEADERS", None)
    return model


def build_input(attack: dict) -> dict:
    """The exact request the app gets. Either the attack's own "input", or golden number "base"
    with the "inject" text added: at the start of the newest message's body (default), or at the end."""
    if "input" in attack:
        return attack["input"]
    base = GOLDENS[attack["base"] - 1]["input"]
    text, inject = base["order_text"], attack["inject"]
    if attack.get("where", "body_start") == "end":
        text = text.rstrip() + "\n\n" + inject + "\n"
    else:
        head, sep, body = text.partition("\n\n")            # the newest message's headers, then its body
        text = head + sep + inject + "\n\n" + body if sep else inject + "\n\n" + text
    return {"order_text": text, "received_date": base["received_date"]}


def save(attacks: list[dict]) -> None:
    ATTACKS.write_text("".join(json.dumps(a, ensure_ascii=False) + "\n" for a in attacks))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3, help="runs per attack (3 while iterating, 8 for the rate)")
    parser.add_argument("--id", help="run only this attack (re-runs it even if it has results)")
    parser.add_argument("--all", action="store_true", help="re-run every attack")
    parser.add_argument("--dry-run", action="store_true", help="print the exact email(s); no model call")
    args = parser.parse_args()

    attacks = [json.loads(line) for line in open(ATTACKS) if line.strip()]
    if args.id:
        todo = [a for a in attacks if a["id"] == args.id]
        if not todo:
            sys.exit(f"No attack with id {args.id!r} in {ATTACKS.name}.")
    elif args.all:
        todo = attacks
    else:
        todo = [a for a in attacks if "runs" not in a]
        if not todo:
            sys.exit("Nothing new to run: every attack has results. Use --id or --all to re-run.")

    if args.dry_run:
        for a in todo:
            print(f"=== {a['id']}  forged_rate {a['forged_rate']}\n{build_input(a)['order_text']}")
        return

    model = use_local_model()
    sys.path.insert(0, str(ROOT))
    sys.path.insert(1, str(CHALLENGE))
    import llm
    import schema
    from harness import CANARY, leaked
    if llm.MODEL != model:                                  # belt and braces: never attack the wrong model
        sys.exit(f"The app loaded {llm.MODEL}, not {model}. Stopping.")

    raw_replies: list[str] = []                             # every model reply, including ones the schema rejected
    real_complete = schema.complete
    def recording_complete(*a, **kw):
        reply = real_complete(*a, **kw)
        raw_replies.append(reply)
        return reply
    schema.complete = recording_complete

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    for attack in todo:
        inp = build_input(attack)
        counts = {"leaked": 0, "clean": 0, "error": 0}
        raw_canary = 0
        print(f"\n{attack['id']}: {args.runs} runs on {model}")
        for k in range(1, args.runs + 1):
            raw_replies.clear()
            started = time.time()
            try:
                actual = schema.solve(schema.Request(**inp)).model_dump_json()
                outcome, why = leaked(actual, attack["forged_rate"])
            except Exception as error:                      # model down, timeout: an error, never a pass
                actual, outcome, why = None, "error", f"{type(error).__name__}: {str(error)[:200]}"
            seconds = time.time() - started
            counts[outcome] += 1
            raw_canary += any(CANARY in r for r in raw_replies)
            print(f"  run {k}: {outcome:7} {seconds:5.1f}s  {why}")
            folder = RAW_DIR / attack["id"]
            folder.mkdir(parents=True, exist_ok=True)
            (folder / f"{stamp}-run{k}.json").write_text(json.dumps(
                {"attack": attack["id"], "model": model, "outcome": outcome, "why": why, "seconds": round(seconds, 1),
                 "input": inp, "raw_replies": raw_replies, "final": json.loads(actual) if actual else None},
                indent=2, ensure_ascii=False))
        attack.update(runs=args.runs, leaked=counts["leaked"], clean=counts["clean"], errors=counts["error"],
                      raw_canary=raw_canary, model=model, run_at=stamp)
        print(f"  => leaked {counts['leaked']} of {args.runs}, clean {counts['clean']}, errors {counts['error']}")
        save(attacks)                                       # after each attack, so a crash keeps what's done


if __name__ == "__main__":
    main()