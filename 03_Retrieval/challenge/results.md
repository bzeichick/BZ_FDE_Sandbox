# TC3 retrieval results

Measured 2026-11-02 20:52 on the production corpus (not committed): 2,636 TMS shipments, 29,418 emails (new text only, deduplicated), 4,919 attachments (rate confirmations excluded). Labels: `use_case/evals/retrieval.jsonl` (redacted copy).

| Technique | Pass | Cited | Calls (avg) | Evidence chars (avg) | Tokens (avg) | Latency s (avg) | Stopped on answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Agentic RAG (BM25) | 7/11 | 9/11 | 9.1 | 29,639 | 113,070 | 37.9 | 8/11 |
| Direct corpus interaction (wiki) | 10/11 | 10/11 | 13.0 | 40,364 | 150,789 | 51.9 | 7/11 |
| Hybrid (BM25 + embeddings, RRF) | 6/11 | 8/11 | 7.7 | 29,972 | 89,999 | 35.3 | 10/11 |
| Wiki + hybrid search (designed after runs 1-3) | 10/11 | 9/11 | 11.8 | 52,439 | 224,035 | 69.7 | 7/11 |

**Settings:** model `anthropic/claude-sonnet-5`, temperature 0 where the provider allows it, max 12 turns, search returns up to 10 records (default 5), 1500 characters of each, no chunking (one record = one unit). as_of and the search filters (customer, after, before) applied before ranking, for both search techniques. Shipment text carries the temperature mode (frozen / refrigerated) next to the range.

**Hybrid:** embeddings `text-embedding-3-small` over the first 8,000 characters of each record; BM25 top 50 + meaning top 50 merged by reciprocal rank fusion (k = 60); reference numbers the agent passes in `exact` are pinned first only if they exist in the data (4-digit years and clock times never count); copies collapsed (attachments: same file; emails: near-identical body with identical numbers).

**Embedding token count:** 9,526,378 tokens for 36,973 records (measured, as reported by the API, 2026-11-02 20:15).

**Wiki:** customer and pickup-facility pages generated from TMS shipments per as_of date (addresses normalized); reads capped at 12,000 characters, grep at 40 lines.

## Per question

| Question | Technique | Pass | Cited | Calls | Evidence chars | Tokens | Latency s | Stopped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | Agentic RAG (BM25) | yes | yes | 7 | 20,426 | 41,915 | 17.12 | answer |
| q01 | Direct corpus interaction (wiki) | yes | yes | 9 | 6,185 | 33,312 | 17.7 | answer |
| q01 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 4 | 11,908 | 28,776 | 15.93 | answer |
| q01 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 3 | 6,697 | 20,973 | 12.04 | answer |
| q02 | Agentic RAG (BM25) | yes | yes | 11 | 34,154 | 138,629 | 58.13 | answer |
| q02 | Direct corpus interaction (wiki) | yes | yes | 19 | 37,663 | 171,817 | 75.95 | max_turns |
| q02 | Hybrid (BM25 + embeddings, RRF) | no | yes | 5 | 30,147 | 51,073 | 41.15 | answer |
| q02 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 5 | 14,991 | 45,786 | 24.23 | answer |
| q03 | Agentic RAG (BM25) | no | no | 3 | 4,912 | 14,863 | 14.42 | answer |
| q03 | Direct corpus interaction (wiki) | yes | yes | 18 | 31,647 | 221,579 | 112.4 | max_turns |
| q03 | Hybrid (BM25 + embeddings, RRF) | no | no | 4 | 16,714 | 33,921 | 22.14 | answer |
| q03 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 19 | 82,863 | 337,950 | 102.48 | max_turns |
| q04 | Agentic RAG (BM25) | yes | yes | 7 | 17,545 | 41,335 | 16.55 | answer |
| q04 | Direct corpus interaction (wiki) | yes | yes | 22 | 43,738 | 291,710 | 59.24 | max_turns |
| q04 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 6 | 15,993 | 38,056 | 18.28 | answer |
| q04 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 9 | 37,177 | 105,773 | 22.22 | answer |
| q05 | Agentic RAG (BM25) | no | yes | 4 | 14,174 | 27,534 | 12.58 | answer |
| q05 | Direct corpus interaction (wiki) | yes | yes | 3 | 25,337 | 47,545 | 9.87 | answer |
| q05 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 7 | 27,338 | 87,598 | 30.39 | answer |
| q05 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 4 | 31,811 | 56,973 | 10.77 | answer |
| q06 | Agentic RAG (BM25) | no | yes | 3 | 8,316 | 14,342 | 7.77 | answer |
| q06 | Direct corpus interaction (wiki) | yes | yes | 3 | 18,283 | 34,936 | 11.05 | answer |
| q06 | Hybrid (BM25 + embeddings, RRF) | no | yes | 6 | 17,017 | 50,282 | 26.09 | answer |
| q06 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 10 | 46,978 | 142,022 | 34.05 | answer |
| q07 | Agentic RAG (BM25) | yes | yes | 15 | 34,968 | 198,509 | 44.13 | max_turns |
| q07 | Direct corpus interaction (wiki) | yes | yes | 11 | 36,907 | 100,313 | 42.56 | answer |
| q07 | Hybrid (BM25 + embeddings, RRF) | no | no | 22 | 70,302 | 262,237 | 95.55 | max_turns |
| q07 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 15 | 56,092 | 274,693 | 101.53 | max_turns |
| q08 | Agentic RAG (BM25) | yes | yes | 8 | 34,567 | 93,300 | 19.61 | answer |
| q08 | Direct corpus interaction (wiki) | yes | yes | 8 | 27,694 | 50,720 | 14.84 | answer |
| q08 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 4 | 20,469 | 39,432 | 15.41 | answer |
| q08 | Wiki + hybrid search (designed after runs 1-3) | yes | no | 11 | 39,253 | 155,164 | 32.02 | answer |
| q09 | Agentic RAG (BM25) | no | no | 21 | 79,730 | 339,407 | 69.42 | max_turns |
| q09 | Direct corpus interaction (wiki) | yes | yes | 24 | 114,469 | 301,658 | 131.34 | answer |
| q09 | Hybrid (BM25 + embeddings, RRF) | no | no | 6 | 28,367 | 67,842 | 25.06 | answer |
| q09 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 30 | 165,413 | 843,580 | 314.25 | max_turns |
| q10 | Agentic RAG (BM25) | yes | yes | 14 | 55,330 | 272,417 | 135.97 | max_turns |
| q10 | Direct corpus interaction (wiki) | no | no | 18 | 84,161 | 363,137 | 78.18 | max_turns |
| q10 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 11 | 52,961 | 191,436 | 63.79 | answer |
| q10 | Wiki + hybrid search (designed after runs 1-3) | no | no | 12 | 51,971 | 274,354 | 74.72 | answer |
| q02b | Agentic RAG (BM25) | yes | yes | 7 | 21,902 | 61,520 | 21.38 | answer |
| q02b | Direct corpus interaction (wiki) | yes | yes | 8 | 17,917 | 41,950 | 17.94 | answer |
| q02b | Hybrid (BM25 + embeddings, RRF) | yes | yes | 10 | 38,472 | 139,341 | 33.99 | answer |
| q02b | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 12 | 43,585 | 207,117 | 38.45 | max_turns |
