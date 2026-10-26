"""Week 3 retrieval: three techniques over the same records, run by the same loop.

  1. Agentic RAG          BM25 keyword search, callable again (Session 5's search_chunks).
  2. Direct corpus        Generated wiki pages (wiki.py) + list / grep / read / read_thread.
     interaction
  3. Hybrid               BM25 + meaning search (embeddings), merged by rank (RRF), with
                          exact reference numbers pinned first and duplicate copies collapsed.

Shared by all three:
  - corpus.py's records (TMS shipments, emails, attachments), cited by ID.
  - as_of and the search filters (customer, after, before) are applied BEFORE ranking,
    never after (the same rule per-user permissions will need in Week 9).
  - one loop (Session 5's run_agent) that ends in a HistoryAnswer (schema.py).
"""

import hashlib
import json
import os
import re
import time
from datetime import date
from functools import cache
from pathlib import Path

import numpy as np
from litellm import completion, embedding
from pydantic import ValidationError
from rank_bm25 import BM25Okapi

from corpus import Record, load_corpus
from llm import MODEL, NUM_RETRIES, TIMEOUT_S, _provider_kwargs
from schema import HistoryAnswer
import wiki

SNIPPET = 1500       # characters of each record shown per search hit (one attachment can be 900K)
MAX_K = 10           # most results one search may return
PAGE_LIMIT = 12000   # characters per read_page / read_thread
GREP_LIMIT = 40      # matching lines returned per grep

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
EMBED_CHARS = 8000   # embed the first 8,000 characters of each record (~2K tokens; giants are capped)
FIRST_STAGE = 50     # hybrid: how many results each side (BM25, meaning) contributes before merging
RRF_K = 60           # hybrid: the standard reciprocal-rank-fusion constant (Session 6)

# ---------------------------------------------------------------------------
# The corpus and the BM25 index, built once and reused (@cache)
# ---------------------------------------------------------------------------

TOKEN = re.compile(r"[a-z0-9$%]+")


def tokenize(text: str) -> list[str]:
    """Lowercase words and numbers. 'PO 6152/SO 70433' -> ['po', '6152', 'so', '70433'],
    so 6152 matches as a whole token, never inside 116152 or a file hash."""
    return TOKEN.findall(text.lower())


@cache
def corpus() -> tuple[list[Record], dict[str, Record]]:
    """All records, and the same records looked up by ID."""
    records = load_corpus()
    return records, {r.id: r for r in records}


@cache
def bm25_index() -> tuple[BM25Okapi, np.ndarray]:
    """BM25 over each record's title + text, plus each record's date for filtering."""
    records, _ = corpus()
    index = BM25Okapi([tokenize(r.title + "\n" + r.text) for r in records])
    dates = np.array([r.date or "9999-12-31" for r in records])   # undated = never visible with as_of
    return index, dates


@cache
def haystacks() -> list[str]:
    """Lowercased text per record, for the customer filter (customer name + title + start of text)."""
    records, _ = corpus()
    return [f"{r.meta.get('customer') or ''} {r.title} {r.text[:3000]}".lower() for r in records]


# ---------------------------------------------------------------------------
# Filters: which records a search may see, decided BEFORE ranking
# ---------------------------------------------------------------------------

FILTERS = {
    "customer": {"type": "string", "description": "Only records that mention this customer name, "
                                                  "as written in the records (part of the name is fine)."},
    "after": {"type": "string", "description": "Only records dated on or after this day, YYYY-MM-DD."},
    "before": {"type": "string", "description": "Only records dated on or before this day, YYYY-MM-DD."},
}


def allowed(as_of: date, customer: str | None = None, after: str | None = None,
            before: str | None = None) -> np.ndarray:
    """True for each record the search may rank: dated by as_of, and inside any filters given."""
    _, dates = bm25_index()
    mask = dates <= as_of.isoformat()
    if after:
        mask &= dates >= date.fromisoformat(after).isoformat()   # a bad date raises; the model sees the error
    if before:
        mask &= dates <= date.fromisoformat(before).isoformat()
    if customer:
        name = customer.lower().strip()
        mask &= np.array([name in h for h in haystacks()])
    return mask


def show(r: Record, also: list[str] | None = None) -> str:
    """How one record appears to the model: its ID first, so it can cite it."""
    text = f"[{r.id}] {r.kind} {r.date} | {r.title}\n{r.text[:SNIPPET]}"
    return text + (f"\n(same content also in: {', '.join(also)})" if also else "")


def tool(name: str, description: str, properties: dict, required=()) -> dict:
    """A tool definition in the format the model expects (same as Session 5's schema())."""
    return {"type": "function", "function": {"name": name, "description": description,
            "parameters": {"type": "object", "properties": properties, "required": list(required)}}}


# ---------------------------------------------------------------------------
# Technique 1: Agentic RAG -- BM25 over every record, callable again
# ---------------------------------------------------------------------------

def bm25_scores(query: str, mask: np.ndarray) -> np.ndarray:
    index, _ = bm25_index()
    return np.where(mask, index.get_scores(tokenize(query)), -np.inf)


def bm25_search(query: str, k: int, mask: np.ndarray) -> list[Record]:
    """The k best-matching allowed records. Empty if nothing matches at all."""
    records, _ = corpus()
    scores = bm25_scores(query, mask)
    top = np.argsort(-scores)[:k]
    return [records[i] for i in top if scores[i] > 0]


def rag_tools(as_of: date) -> tuple[list[dict], dict]:
    """The tools for one question: definitions for the model, and the Python functions behind them."""

    def search_records(query: str, k: int = 5, customer: str | None = None,
                       after: str | None = None, before: str | None = None) -> str:
        hits = bm25_search(query, max(1, min(k, MAX_K)), allowed(as_of, customer, after, before))
        return "\n\n---\n\n".join(show(r) for r in hits) or "(no matching records)"

    tools = [tool(
        "search_records",
        "Keyword search (BM25) over the broker's TMS shipments, order emails and email "
        "attachments dated on or before today. Returns the best matches, each starting with "
        "its record ID in [brackets]. Narrow with customer / after / before. Search again with "
        "different words or an exact reference number when the evidence is incomplete.",
        {"query": {"type": "string", "description": "Words to search for."},
         "k": {"type": "integer", "description": f"How many results, 1 to {MAX_K}. Default 5."},
         **FILTERS},
        ["query"],
    )]
    return tools, {"search_records": search_records}


# ---------------------------------------------------------------------------
# Technique 2: Direct corpus interaction -- named pages, an index, list / grep / read
# ---------------------------------------------------------------------------

def show_full(r: Record) -> str:
    """One whole record (capped), for read_page."""
    return f"[{r.id}] {r.kind} {r.date} | {r.title}\n{r.text[:PAGE_LIMIT]}"


def dci_tools(as_of: date) -> tuple[list[dict], dict]:
    """The wiki tools for one question, over pages and records dated on or before as_of."""
    records, by_id = corpus()
    cutoff = as_of.isoformat()
    visible = [r for r in records if r.date and r.date <= cutoff]
    visible_ids = {r.id for r in visible}
    pages = wiki.pages_for(records, as_of)

    def list_pages() -> str:
        return pages["index"]

    def grep(pattern: str) -> str:
        try:
            rx = re.compile(pattern, re.I)
        except re.error:
            rx = re.compile(re.escape(pattern), re.I)
        hits, more = [], 0
        named = list(pages.items()) + [(r.id, r.text) for r in visible]
        for name, text in named:
            if not rx.search(text):
                continue
            if len(hits) >= GREP_LIMIT:
                more += 1          # keep counting, so "how many records mention X" stays answerable
                continue
            for number, line in enumerate(text.splitlines(), 1):
                if rx.search(line) and len(hits) < GREP_LIMIT:
                    hits.append(f"{name}:{number}: {line.strip()[:200]}")
        if not hits:
            return "(no matches)"
        return "\n".join(hits) + (f"\n(+{more} more pages/records also match; narrow the pattern)" if more else "")

    def read_page(page: str) -> str:
        if page in pages:
            return pages[page][:PAGE_LIMIT]
        if page in visible_ids:
            return show_full(by_id[page])
        return f"(no page or record named {page!r}; use list_pages or grep)"

    def read_thread(record_id: str) -> str:
        email_id = record_id.split("#")[0]
        email = by_id.get(email_id)
        if not email or email.kind != "email" or email_id not in visible_ids:
            return f"(no email named {record_id!r})"
        thread = [r for r in visible if r.kind == "email" and r.meta.get("thread") == email.meta.get("thread")]
        thread.sort(key=lambda r: r.meta.get("sent") or r.date)
        text = "\n\n=====\n\n".join(f"[{r.id}]\n{r.text}" for r in thread)
        return f"{len(thread)} messages, oldest first:\n\n" + text[:PAGE_LIMIT]

    tools = [
        tool("list_pages", "Read the index: every customer page and pickup-facility page, with shipment counts.", {}),
        tool("grep", "Search exact text or a regular expression across every page and record (shipments, emails, "
                     "attachments). Returns matching lines as name:line: text, and how many more match.",
             {"pattern": {"type": "string"}}, ["pattern"]),
        tool("read_page", "Read one page by name (customer:<name>, facility:<address>, index) or one record by its ID "
                          "(84477, msg:16250, msg:16250#att1). Customer and facility pages carry counts and shares "
                          "with the shipment IDs behind them: cite those shipment IDs.",
             {"page": {"type": "string"}}, ["page"]),
        tool("read_thread", "Read every message in an email's thread, oldest first, to see what a short reply "
                            "('Sure, that will be fine') agreed to.",
             {"record_id": {"type": "string", "description": "Any email ID in the thread, e.g. msg:120711."}},
             ["record_id"]),
    ]
    funcs = {"list_pages": list_pages, "grep": grep, "read_page": read_page, "read_thread": read_thread}
    return tools, funcs


# ---------------------------------------------------------------------------
# Technique 3: Hybrid -- BM25 + meaning search, merged by rank
# ---------------------------------------------------------------------------

def embed_text(r: Record) -> str:
    """What gets embedded for a record: its title and the start of its text (capped)."""
    return (r.title + "\n" + r.text)[:EMBED_CHARS] or r.id


def embed_texts(texts: list[str], progress: bool = False) -> tuple[np.ndarray, int]:
    """Embed many texts in batches. Returns unit-length vectors and the tokens the API reported."""
    vectors, tokens, batch, size = [], 0, [], 0

    def send(batch):
        nonlocal tokens
        response = embedding(model=EMBED_MODEL, input=batch, timeout=120, num_retries=5)
        vectors.extend(item["embedding"] for item in response.data)
        tokens += (getattr(response, "usage", None) and response.usage.total_tokens) or 0
        if progress:
            print(f"  embedded {len(vectors):,}/{len(texts):,}  ({tokens:,} tokens so far)", flush=True)

    for text in texts:
        # OpenAI allows 2,048 inputs and 300K tokens per request; 250K characters keeps us under both.
        if batch and (size + len(text) > 250_000 or len(batch) >= 2000):
            send(batch)
            batch, size = [], 0
        batch.append(text)
        size += len(text)
    if batch:
        send(batch)
    matrix = np.array(vectors, dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12   # unit length: dot product = cosine
    return matrix, tokens


def embed_path() -> Path:
    """Where the vectors live. Production vectors encode real orders, so they go in the gitignored
    use_case/data/, never next to the code; the synthetic ones can sit in corpus/."""
    if os.environ.get("COLDLADE_DB"):
        for parent in Path(__file__).resolve().parents:
            if (parent / "use_case" / "data").is_dir():
                return parent / "use_case" / "data" / "embeddings_production"
        raise SystemExit("Production embeddings must go in use_case/data/ (gitignored), which wasn't found.")
    return Path(__file__).parent / "corpus" / "embeddings_synthetic"


def fingerprint(texts: list[str]) -> str:
    """A short hash of exactly what was embedded, so a change to corpus.py's text can't go unnoticed."""
    return hashlib.sha256("\x00".join(texts).encode()).hexdigest()[:16]


def embedding_info() -> dict | None:
    """The saved run's model, record count and measured token count (for results.md), if any."""
    meta = embed_path().with_suffix(".json")
    if not meta.exists():
        return None
    info = json.loads(meta.read_text())
    return {k: v for k, v in info.items() if k != "ids"}


@cache
def dense_index() -> np.ndarray:
    """One unit vector per record, in corpus order. Built by `python embed.py` for production;
    a small corpus (the shipped synthetic one) is embedded on first use instead."""
    records, _ = corpus()
    path = embed_path()
    if path.with_suffix(".npy").exists():
        meta = json.loads(path.with_suffix(".json").read_text())
        current = fingerprint([embed_text(r) for r in records])
        if meta["ids"] != [r.id for r in records] or meta["model"] != EMBED_MODEL or meta.get("fingerprint") != current:
            raise SystemExit("The saved embeddings don't match the corpus text or EMBED_MODEL: run `python embed.py`.")
        return np.load(path.with_suffix(".npy"))
    if len(records) <= 5000:
        return embed_texts([embed_text(r) for r in records])[0]
    raise SystemExit("No embeddings for this corpus yet: run `python embed.py` first.")


def dense_scores(query: str, mask: np.ndarray) -> np.ndarray:
    vectors = dense_index()
    query_vector = embed_texts([query])[0][0]
    return np.where(mask, vectors @ query_vector, -np.inf)


# --- Tweak 3: reference numbers named by the agent, confirmed against the data, pinned first ---

REF_LABEL = re.compile(r"\b(?:load\s+tender|po|so|bol|load|order|tender|ref|conf(?:irmation)?)\s*#?\s*:?\s*"
                       r"([a-z0-9][a-z0-9_-]{3,})", re.I)
REF_LINES = ("Shipment ", "Customer PO:", "Pickup reference:")   # whole-field reference numbers


def is_ref_token(token: str) -> bool:
    """A reference-number token: 4+ characters with at least 3 digits ('6152', 'so050414').
    Four plain digits that read as a year (1990-2039) or a clock time (0000-2359) are not references:
    the agent's queries are full of '2026', '1230' and '1300', and those match thousands of records."""
    if len(token) < 4 or sum(ch.isdigit() for ch in token) < 3:
        return False
    if len(token) == 4 and token.isdigit():
        n = int(token)
        if 1990 <= n <= 2039 or (n // 100 <= 23 and n % 100 <= 59):
            return False
    return True


@cache
def known_refs() -> frozenset[str]:
    """Every reference number in the data: the TMS reference fields of each shipment, plus numbers
    labelled PO / SO / BOL / load / tender / ref in email and attachment titles."""
    records, _ = corpus()
    refs = set()
    for r in records:
        if r.kind == "shipment":
            lines = [l.split(":", 1)[-1] if ":" in l else l for l in r.text.splitlines() if l.startswith(REF_LINES)]
            appt = next((l for l in r.text.splitlines() if l.startswith("Delivery appointment:")), "")
            lines += [m.group(1) for m in REF_LABEL.finditer(appt)]   # 'Confirmation # 447071', not the times
        else:
            lines = [m.group(1) for m in REF_LABEL.finditer(r.title)]
        refs.update(t for line in lines for t in tokenize(line) if is_ref_token(t))
    return frozenset(refs)


def confirm_refs(candidates: list[str]) -> tuple[list[str], list[str]]:
    """Split what the agent called reference numbers into confirmed (in the data) and rejected."""
    refs = known_refs()
    confirmed, rejected = [], []
    for candidate in candidates or []:
        tokens = [t for t in tokenize(str(candidate)) if is_ref_token(t)]
        hits = [t for t in tokens if t in refs]
        if hits:
            confirmed.extend(hits)
        else:
            rejected.append(str(candidate))
    return confirmed, rejected


# --- Tweak 4: collapse copies, never drop them ---

def _body(r: Record) -> str:
    return r.text.split("\n\n", 1)[-1].lower()   # emails: skip the header lines (Subject/From/To/Sent)


def same_content(a: Record, b: Record) -> bool:
    """Copies, not look-alikes. Attachments: the same file (same sha). Emails: near-identical body
    AND exactly the same numbers -- so a reschedule (10/5 -> 10/8) or a revised rate is never collapsed."""
    if a.kind == b.kind == "attachment":
        return bool(a.meta.get("sha")) and a.meta.get("sha") == b.meta.get("sha")
    if a.kind == b.kind == "email":
        ta, tb = _body(a), _body(b)
        if re.findall(r"\d+", ta) != re.findall(r"\d+", tb):
            return False
        wa, wb = set(ta.split()), set(tb.split())
        return len(wa & wb) / max(1, len(wa | wb)) >= 0.9
    return False


def collapse(hits: list[Record], k: int) -> list[tuple[Record, list[str]]]:
    """The first k distinct records, each with the IDs of its copies."""
    kept: list[tuple[Record, list[str]]] = []
    for r in hits:
        twin = next((group for group in kept if same_content(group[0], r)), None)
        if twin:
            twin[1].append(r.id)
        elif len(kept) < k:
            kept.append((r, []))
    return kept


def hybrid_search(query: str, k: int, mask: np.ndarray, exact: list[str] | None = None):
    """Pinned exact matches first, then BM25 and meaning search merged by rank (RRF), copies collapsed."""
    records, _ = corpus()
    notes = []
    confirmed, rejected = confirm_refs(exact or [])
    if rejected:
        notes.append(f"not a known reference number, searched normally: {', '.join(rejected)}")

    # Pinned: allowed records containing a confirmed reference as a whole token, best BM25 first.
    pinned: list[int] = []
    if confirmed:
        index, _ = bm25_index()
        scores = bm25_scores(" ".join(confirmed), mask)
        pinned = [int(i) for i in np.argsort(-scores) if scores[i] > 0
                  and mask[i] and any(t in index.doc_freqs[i] for t in confirmed)][:k]
        notes.append(f"exact match for {', '.join(confirmed)}: {len(pinned)} record(s), listed first")

    # Merge by rank, not score: BM25 and cosine scores aren't on the same scale (Session 6).
    fused: dict[int, float] = {}
    for scores in (bm25_scores(query, mask), dense_scores(query, mask)):
        ranked = [int(i) for i in np.argsort(-scores)[:FIRST_STAGE] if np.isfinite(scores[i]) and scores[i] > 0]
        for rank, i in enumerate(ranked):
            fused[i] = fused.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
    order = pinned + [i for i in sorted(fused, key=fused.get, reverse=True) if i not in pinned]
    return collapse([records[i] for i in order[: k * 3]], k), notes


def hybrid_tools(as_of: date) -> tuple[list[dict], dict]:
    """Technique 3's one tool: the same search_records shape as technique 1, ranked by hybrid_search."""

    def search_records(query: str, k: int = 5, customer: str | None = None, after: str | None = None,
                       before: str | None = None, exact: list[str] | None = None) -> str:
        hits, notes = hybrid_search(query, max(1, min(k, MAX_K)), allowed(as_of, customer, after, before), exact)
        body = "\n\n---\n\n".join(show(r, also) for r, also in hits) or "(no matching records)"
        return ("\n".join(f"({n})" for n in notes) + "\n\n" if notes else "") + body

    tools = [tool(
        "search_records",
        "Search the broker's TMS shipments, order emails and email attachments dated on or before "
        "today, by keywords AND by meaning (finds records that say the same thing in other words). "
        "Returns the best matches, each starting with its record ID in [brackets]; copies of the same "
        "content are shown once. Narrow with customer / after / before. Put any reference numbers "
        "from the question (PO, SO, BOL, load or shipment numbers) in `exact`: records containing "
        "them are listed first. Dates, times, temperatures and ZIP codes are not reference numbers.",
        {"query": {"type": "string", "description": "What to search for, in words."},
         "k": {"type": "integer", "description": f"How many results, 1 to {MAX_K}. Default 5."},
         **FILTERS,
         "exact": {"type": "array", "items": {"type": "string"},
                   "description": "Reference numbers to match exactly, e.g. [\"6152\"]."}},
        ["query"],
    )]
    return tools, {"search_records": search_records}


# ---------------------------------------------------------------------------
# The loop (Session 5's run_agent), ending in a HistoryAnswer
# ---------------------------------------------------------------------------

SYSTEM = """You answer questions from a freight broker's order desk using only the broker's own records:
TMS shipments, order emails, and email attachments. Today is {today}; records after that date don't exist yet.

- Investigate with the tools before answering. Records may use different words than the question,
  so if a search comes back thin, search again another way.
- Stop as soon as the records answer the question. Mention small differences between records
  (e.g. 12:30 in the TMS vs 1pm in an email) in the answer instead of investigating them.
- Use only what the records say. If they don't answer the question, set declined to true and say so
  plainly; never fill the gap with a number from a record that only looks related.
- A customer or facility page may be cited (kind "profile"), but only together with at least three of
  the shipment IDs it lists behind the number you use: a page is a summary, the shipments are the proof.
- Cite every record you rely on by its exact ID (e.g. 84477, msg:16250, msg:16250#att1) with a quote
  copied from it. List what you searched, and what it found, in `searched`.
- When you are done, reply with ONLY a JSON object (no other text) matching this schema:
{schema}"""


PAGE_PREFIXES = ("customer:", "facility:", "index")


def page_without_ids(answer: HistoryAnswer) -> bool:
    """True if the answer cites a wiki page without at least three TMS shipment IDs beside it."""
    ids = [s.record_id for s in answer.sources]
    return any(i.startswith(PAGE_PREFIXES) for i in ids) and sum(i.isdigit() for i in ids) < 3


def ask_model(messages: list[dict], tools: list[dict], tool_choice: str | None = None):
    """One model turn with tools offered. Same model and settings as the rest of the app (llm.py).
    tool_choice="none" forbids tool calls for this turn (used for the final, out-of-turns answer)."""
    extra = {"tool_choice": tool_choice} if tool_choice else {}
    response = completion(model=MODEL, messages=messages, tools=tools, temperature=0, drop_params=True,
                          timeout=TIMEOUT_S, num_retries=NUM_RETRIES, **extra, **_provider_kwargs())
    return response.choices[0].message, getattr(response, "usage", None)  # type: ignore


def run_agent(question: str, as_of: date, tools: list[dict], funcs: dict, max_turns: int = 8) -> dict:
    """Let the model call tools until it answers or runs out of turns.

    Returns the HistoryAnswer (None if the model never produced a valid one) and the trace
    Step 3 scores: every tool call, evidence characters read, tokens, latency, how it stopped.
    """
    system = SYSTEM.format(today=as_of.isoformat(), schema=json.dumps(HistoryAnswer.model_json_schema()))
    messages = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    trace: list[dict] = []
    totals = {"evidence_chars": 0, "tokens_in": 0, "tokens_out": 0}
    started = time.perf_counter()

    def finish(answer, stopped):
        return {"answer": answer, "trace": trace, **totals,
                "latency_s": round(time.perf_counter() - started, 2), "stopped": stopped}

    def count(usage):
        if usage:
            totals["tokens_in"] += usage.prompt_tokens
            totals["tokens_out"] += usage.completion_tokens

    asked_to_fix = asked_for_ids = False
    for _ in range(max_turns):
        msg, usage = ask_model(messages, tools)
        count(usage)
        calls = msg.tool_calls or []

        if not calls:   # no tool call means this is the final answer
            text = msg.content or ""
            try:
                answer = HistoryAnswer.model_validate_json(text[text.find("{"): text.rfind("}") + 1])
            except ValidationError as error:
                if asked_to_fix:
                    return finish(None, "bad_json")
                asked_to_fix = True   # one retry with the error, like solve() in Week 1
                messages += [{"role": "assistant", "content": text},
                             {"role": "user", "content": f"That didn't match the schema: {str(error)[:1000]}\n"
                                                         "Reply with the corrected JSON only."}]
                continue
            if page_without_ids(answer) and not asked_for_ids:
                asked_for_ids = True  # one reply, same pattern: a page alone can't be checked in the TMS
                messages += [{"role": "assistant", "content": text},
                             {"role": "user", "content": "You cited a page without the shipment IDs behind it. Keep "
                                                         "the page if you like, and add at least three shipment IDs "
                                                         "listed on it as sources (kind \"shipment\", quoting the line "
                                                         "each appears on). Reply with the corrected JSON only."}]
                continue
            return finish(answer, "answer")

        # Run each tool the model asked for, and hand the results back (unchanged from Session 5).
        shaped = [{"id": c.id, "type": "function",
                   "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]
        messages.append({"role": "assistant", "content": msg.content or "", "tool_calls": shaped})
        for call in shaped:
            name, args = call["function"]["name"], {}
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
                result = str(funcs[name](**args))
            except Exception as exc:
                result = f"(tool error: {type(exc).__name__}: {exc})"
            totals["evidence_chars"] += len(result)
            trace.append({"tool": name, "args": args, "chars": len(result)})
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})

    # Out of turns: one last call that may not use tools, so the desk still gets what was found,
    # marked partial, instead of nothing (Session 5: say when the loop ran out).
    messages.append({"role": "user", "content": "You are out of tool calls. Reply now with ONLY the JSON "
                                                "object, from the evidence above, with partial set to true."})
    msg, usage = ask_model(messages, tools, tool_choice="none")
    count(usage)
    text = msg.content or ""
    try:
        answer = HistoryAnswer.model_validate_json(text[text.find("{"): text.rfind("}") + 1])
        answer.partial = True
    except ValidationError:
        answer = HistoryAnswer(answer="Stopped before finishing: the turn budget ran out.",
                               as_of=as_of, partial=True)
    return finish(answer, "max_turns")

# ---------------------------------------------------------------------------
# Technique 4 (designed AFTER final runs 1-3): the wiki's tools plus hybrid's search
# ---------------------------------------------------------------------------

def combined_tools(as_of: date) -> tuple[list[dict], dict]:
    """The wiki tools (list_pages, grep, read_page, read_thread) and hybrid's search_records, together.
    The search tool's description says when to use which: a search returns a sample, not a count."""
    wiki_tools, wiki_funcs = dci_tools(as_of)
    search_tools, search_funcs = hybrid_tools(as_of)
    search_tools[0]["function"]["description"] += (
        " Use this to find specific records fast (a PO, an email, a load). For questions about patterns "
        "or sets ('usually', 'how many', 'which customers'), read the customer or facility pages instead "
        "(list_pages, read_page): a search returns a sample, not a count.")
    return wiki_tools + search_tools, {**wiki_funcs, **search_funcs}