# TC3 retrieval results

Measured 2026-11-02 21:17 on the production corpus (not committed): 2,636 TMS shipments, 30,680 emails (new text only, deduplicated), 4,919 attachments (rate confirmations excluded). Labels: `use_case/evals/retrieval.jsonl` (redacted copy).

| Technique | Pass | Cited | Calls (avg) | Evidence chars (avg) | Tokens (avg) | Latency s (avg) | Stopped on answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Direct corpus interaction (wiki) | 8/10 | 8/10 | 20.2 | 57,365 | 247,855 | 71.9 | 2/10 |

**Settings:** model `anthropic/claude-sonnet-5`, temperature 0 where the provider allows it, max 12 turns, search returns up to 10 records (default 5), 1500 characters of each, no chunking (one record = one unit). as_of and the search filters (customer, after, before) applied before ranking, for both search techniques. Shipment text carries the temperature mode (frozen / refrigerated) next to the range.

**Hybrid:** embeddings `text-embedding-3-small` over the first 8,000 characters of each record; BM25 top 50 + meaning top 50 merged by reciprocal rank fusion (k = 60); reference numbers the agent passes in `exact` are pinned first only if they exist in the data (4-digit years and clock times never count); copies collapsed (attachments: same file; emails: near-identical body with identical numbers).

**Embedding token count:** 9,526,378 tokens for 36,973 records (measured, as reported by the API, 2026-11-02 20:15).

**Wiki:** customer and pickup-facility pages generated from TMS shipments per as_of date (addresses normalized); reads capped at 12,000 characters, grep at 40 lines.

## Per question

| Question | Technique | Pass | Cited | Calls | Evidence chars | Tokens | Latency s | Stopped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| u01 | Direct corpus interaction (wiki) | yes | yes | 21 | 77,706 | 439,598 | 141.01 | max_turns |
| u02 | Direct corpus interaction (wiki) | yes | yes | 35 | 137,998 | 511,947 | 66.26 | max_turns |
| u03 | Direct corpus interaction (wiki) | no | no | 25 | 71,033 | 295,960 | 56.81 | max_turns |
| u04 | Direct corpus interaction (wiki) | yes | yes | 23 | 41,519 | 210,745 | 74.6 | max_turns |
| u05 | Direct corpus interaction (wiki) | yes | yes | 20 | 58,273 | 301,377 | 130.94 | max_turns |
| u06 | Direct corpus interaction (wiki) | yes | yes | 20 | 57,545 | 285,620 | 88.35 | max_turns |
| u07 | Direct corpus interaction (wiki) | yes | yes | 8 | 25,915 | 59,552 | 16.06 | answer |
| u08 | Direct corpus interaction (wiki) | no | no | 23 | 44,634 | 165,335 | 57.44 | max_turns |
| u09 | Direct corpus interaction (wiki) | yes | yes | 11 | 33,309 | 72,887 | 23.69 | answer |
| u10 | Direct corpus interaction (wiki) | yes | yes | 16 | 25,719 | 135,526 | 64.18 | max_turns |
