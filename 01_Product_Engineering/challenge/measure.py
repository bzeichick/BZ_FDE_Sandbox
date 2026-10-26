"""Step 3: run each retrieval technique over the labelled questions, and score it.

    uv run python measure.py                       # every technique, every question
    uv run python measure.py --only rag --q q01    # one technique, one question (for debugging)

Needs COLDLADE_DB set: the labels point at production records, so they can only be scored there.

Reads:  use_case/data/retrieval.real.jsonl       (production labels; gitignored)
Writes: 03_Retrieval/challenge/results.md         (numbers and question IDs only, safe to commit)
        use_case/data/runs/<time>.jsonl           (every answer and trace, for reading; gitignored)

Scoring follows Session 5: pass = the reviewed terms are in the answer; cited = every gold
record is in the answer's sources; and the trace (calls, evidence, latency, how it stopped)
sits next to both, because a right answer can hide a wasteful search.
"""

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

import retrieval
from llm import MODEL

REPO = Path(__file__).resolve().parents[2]
LABELS = REPO / "use_case" / "data" / "retrieval.real.jsonl"
RESULTS = REPO / "03_Retrieval" / "challenge" / "results.md"
RUNS = REPO / "use_case" / "data" / "runs"

MAX_TURNS = 8

# Each technique is a name and a function that returns (tool definitions, tool functions)
# for one question's as_of date. Steps 3c and 3d add the other two here.
TECHNIQUES = {
    "rag": ("Agentic RAG (BM25)", retrieval.rag_tools),
    "dci": ("Direct corpus interaction (wiki)", retrieval.dci_tools),
    "hybrid": ("Hybrid (BM25 + embeddings, RRF)", retrieval.hybrid_tools),
    "combo": ("Wiki + hybrid search (designed after runs 1-3)", retrieval.combined_tools),
}

def has(text: str, term) -> bool:
    """A must_contain term is a string, or a list where any one spelling counts."""
    return any(t.lower() in text for t in (term if isinstance(term, list) else [term]))


def cites(sources: list[str], record_id: str) -> bool:
    """Citing an email's attachment (msg:16250#att1) counts as citing the email (msg:16250)."""
    return any(s == record_id or s.startswith(record_id + "#") for s in sources)


def score(label: dict, run: dict) -> dict:
    answer = run["answer"]
    text = answer.answer.lower() if answer else ""
    sources = [s.record_id for s in answer.sources] if answer else []

    wrong_cites = [x for x in label.get("must_not_cite", []) if cites(sources, x)]
    # must_not_contain: phrases that fail the answer even when the keywords match
    # (catches confident wrong answers like "every shipment picks up at...").
    blocked = [t for t in label.get("must_not_contain", []) if has(text, t)]
    # A decline question also needs the answer to actually decline, not just use the words.
    declined_ok = answer.declined if (answer and label["kind"] == "decline") else True
    passed = (bool(answer) and all(has(text, t) for t in label["must_contain"])
              and not blocked and not wrong_cites and declined_ok)

    if label.get("gold_rule"):   # pattern questions: enough shipments from the right customer
        rule = label["gold_rule"]
        _, by_id = retrieval.corpus()
        n = sum(1 for s in sources if s in by_id and by_id[s].meta.get("customer") == rule["customer"])
        cited = n >= rule["min_cites"]
    else:                        # every gold record cited (a decline's gold is empty: nothing required)
        # A gold entry may be a list of alternatives: any one of them proves that part of the answer.
        cited = all(any(cites(sources, alt) for alt in (g if isinstance(g, list) else [g]))
                    for g in label["gold"])

    return {"pass": passed, "cited": bool(answer) and cited and not wrong_cites,
            "calls": len(run["trace"]), "evidence_chars": run["evidence_chars"],
            "tokens": run["tokens_in"] + run["tokens_out"], "latency_s": run["latency_s"],
            "stopped": run["stopped"]}


def write_results(rows: list[dict]) -> None:
    """The results table: one summary row per technique, then every question. No question text."""
    records, _ = retrieval.corpus()
    kinds = {k: sum(1 for r in records if r.kind == k) for k in ("shipment", "email", "attachment")}
    lines = [
        "# TC3 retrieval results",
        "",
        f"Measured {datetime.now():%Y-%m-%d %H:%M} on the production corpus (not committed): "
        f"{kinds['shipment']:,} TMS shipments, {kinds['email']:,} emails (new text only, deduplicated), "
        f"{kinds['attachment']:,} attachments (rate confirmations excluded). "
        "Labels: `use_case/evals/retrieval.jsonl` (redacted copy).",
        "",
        "| Technique | Pass | Cited | Calls (avg) | Evidence chars (avg) | Tokens (avg) | Latency s (avg) | Stopped on answer |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for key, (label, _) in TECHNIQUES.items():
        rs = [r for r in rows if r["technique"] == key]
        if not rs:
            continue
        n = len(rs)
        avg = lambda f: sum(r[f] for r in rs) / n
        lines.append(f"| {label} | {sum(r['pass'] for r in rs)}/{n} | {sum(r['cited'] for r in rs)}/{n} | "
                     f"{avg('calls'):.1f} | {avg('evidence_chars'):,.0f} | {avg('tokens'):,.0f} | "
                     f"{avg('latency_s'):.1f} | {sum(r['stopped'] == 'answer' for r in rs)}/{n} |")
    lines += [
        "",
        f"**Settings:** model `{MODEL}`, temperature 0 where the provider allows it, max {MAX_TURNS} turns, "
        f"search returns up to {retrieval.MAX_K} records (default 5), {retrieval.SNIPPET} characters of each, "
                "no chunking (one record = one unit). as_of and the search filters (customer, after, before) "
        "applied before ranking, for both search techniques. Shipment text carries the temperature mode "
        "(frozen / refrigerated) next to the range.",
        "",
        f"**Hybrid:** embeddings `{retrieval.EMBED_MODEL}` over the first {retrieval.EMBED_CHARS:,} characters "
        f"of each record; BM25 top {retrieval.FIRST_STAGE} + meaning top {retrieval.FIRST_STAGE} merged by "
        f"reciprocal rank fusion (k = {retrieval.RRF_K}); reference numbers the agent passes in `exact` are "
        "pinned first only if they exist in the data (4-digit years and clock times never count); copies "
        "collapsed (attachments: same file; emails: near-identical body with identical numbers).",
        "",
        "**Embedding token count:** " + (
            f"{info['tokens']:,} tokens for {info['records']:,} records (measured, as reported by the API, "
            f"{info['date']})." if (info := retrieval.embedding_info()) else "n/a (no embeddings built)."),
        "",
        "**Wiki:** customer and pickup-facility pages generated from TMS shipments per as_of date "
        f"(addresses normalized); reads capped at {retrieval.PAGE_LIMIT:,} characters, grep at "
        f"{retrieval.GREP_LIMIT} lines.",
        "",
        "## Per question",
        "",
        "| Question | Technique | Pass | Cited | Calls | Evidence chars | Tokens | Latency s | Stopped |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        lines.append(f"| {r['id']} | {TECHNIQUES[r['technique']][0]} | {'yes' if r['pass'] else 'no'} | "
                     f"{'yes' if r['cited'] else 'no'} | {r['calls']} | {r['evidence_chars']:,} | "
                     f"{r['tokens']:,} | {r['latency_s']} | {r['stopped']} |")
    RESULTS.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score retrieval techniques against the labelled questions.")
    parser.add_argument("--only", choices=sorted(TECHNIQUES), help="run one technique")
    parser.add_argument("--q", help="run one question id, e.g. q07")
    parser.add_argument("--resume", help="an interrupted run's use_case/data/runs/<time>.jsonl: keep its results, run the rest")
    args = parser.parse_args()
    if not os.environ.get("COLDLADE_DB"):
        raise SystemExit("Set COLDLADE_DB to orders.db first: the labels point at production records.")

    labels = [json.loads(line) for line in LABELS.read_text().splitlines() if line.strip()]
    labels = [l for l in labels if not args.q or l["id"] == args.q]
    techniques = [args.only] if args.only else list(TECHNIQUES)

    RUNS.mkdir(exist_ok=True)
    if args.resume:   # keep what an interrupted run already saved; only run the missing (question, technique) pairs
        run_log = Path(args.resume).resolve()
        saved = [json.loads(line) for line in run_log.read_text().splitlines() if line.strip()]
    else:
        run_log = RUNS / f"{datetime.now():%Y%m%d_%H%M%S}.jsonl"
        saved = []
    columns = ("id", "technique", "pass", "cited", "calls", "evidence_chars", "tokens", "latency_s", "stopped")
    rows = [{c: s[c] for c in columns} for s in saved]
    finished = {(r["id"], r["technique"]) for r in rows}
    with open(run_log, "a") as log:
        for label in labels:
            for key in techniques:
                if (label["id"], key) in finished:
                    continue
                as_of = date.fromisoformat(label["as_of"])
                tools, funcs = TECHNIQUES[key][1](as_of)
                run = retrieval.run_agent(label["question"], as_of, tools, funcs, max_turns=MAX_TURNS)
                row = {"id": label["id"], "technique": key, **score(label, run)}
                rows.append(row)
                print(f"{label['id']} {key:4} pass={row['pass']!s:5} cited={row['cited']!s:5} "
                      f"calls={row['calls']} chars={row['evidence_chars']:,} {row['latency_s']}s {row['stopped']}",
                      flush=True)
                answer = run["answer"].model_dump(mode="json") if run["answer"] else None
                log.write(json.dumps({**row, "question": label["question"], "answer": answer,
                                      "trace": run["trace"]}) + "\n")
    write_results(rows)
    print(f"\nwrote {RESULTS.relative_to(REPO)}  and every trace to {run_log.relative_to(REPO)}")


if __name__ == "__main__":
    main()