# TC3 retrieval results

Measured 2026-10-27 11:36 on the production corpus (not committed): 2,636 TMS shipments, 30,680 emails (new text only, deduplicated), 4,919 attachments (rate confirmations excluded). Labels: `use_case/evals/retrieval.jsonl` (redacted copy).

| Technique | Pass | Cited | Calls (avg) | Evidence chars (avg) | Tokens (avg) | Latency s (avg) | Stopped on answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Direct corpus interaction (wiki) | 8/10 | 9/10 | 12.9 | 36,176 | 113,551 | 31.1 | 3/10 |

**Settings:** model `anthropic/claude-sonnet-5`, temperature 0 where the provider allows it, max 8 turns, search returns up to 10 records (default 5), 1500 characters of each, no chunking (one record = one unit). as_of and the search filters (customer, after, before) applied before ranking, for both search techniques. Shipment text carries the temperature mode (frozen / refrigerated) next to the range.

**Hybrid:** embeddings `text-embedding-3-small` over the first 8,000 characters of each record; BM25 top 50 + meaning top 50 merged by reciprocal rank fusion (k = 60); reference numbers the agent passes in `exact` are pinned first only if they exist in the data (4-digit years and clock times never count); copies collapsed (attachments: same file; emails: near-identical body with identical numbers).

**Embedding token count:** 9,526,378 tokens for 36,973 records (measured, as reported by the API, 2026-10-26 10:52).

**Wiki:** customer and pickup-facility pages generated from TMS shipments per as_of date (addresses normalized); reads capped at 12,000 characters, grep at 40 lines.

## Per question

| Question | Technique | Pass | Cited | Calls | Evidence chars | Tokens | Latency s | Stopped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| u01 | Direct corpus interaction (wiki) | yes | yes | 18 | 67,331 | 248,272 | 62.28 | max_turns |
| u03 | Direct corpus interaction (wiki) | no | no | 19 | 54,831 | 188,385 | 37.72 | max_turns |
| u04 | Direct corpus interaction (wiki) | yes | yes | 14 | 36,123 | 112,663 | 28.95 | max_turns |
| u05 | Direct corpus interaction (wiki) | yes | yes | 13 | 43,496 | 147,189 | 27.58 | max_turns |
| u06 | Direct corpus interaction (wiki) | no | yes | 9 | 20,417 | 50,313 | 34.66 | answer |
| u07 | Direct corpus interaction (wiki) | yes | yes | 11 | 37,157 | 101,440 | 22.23 | answer |
| u08 | Direct corpus interaction (wiki) | yes | yes | 13 | 12,435 | 53,268 | 28.48 | max_turns |
| u10 | Direct corpus interaction (wiki) | yes | yes | 6 | 1,881 | 17,528 | 10.13 | answer |
| u02 | Direct corpus interaction (wiki) | yes | yes | 16 | 68,552 | 161,856 | 39.02 | max_turns |
| u09 | Direct corpus interaction (wiki) | yes | yes | 10 | 19,535 | 54,596 | 19.99 | max_turns |
