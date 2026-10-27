# TC3 retrieval results

Measured 2026-10-26 18:27 on the production corpus (not committed): 2,636 TMS shipments, 29,418 emails (new text only, deduplicated), 4,919 attachments (rate confirmations excluded). Labels: `use_case/evals/retrieval.jsonl` (redacted copy).

| Technique | Pass | Cited | Calls (avg) | Evidence chars (avg) | Tokens (avg) | Latency s (avg) | Stopped on answer |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Agentic RAG (BM25) | 5/10 | 7/10 | 7.0 | 26,782 | 67,980 | 22.1 | 8/10 |
| Direct corpus interaction (wiki) | 10/10 | 10/10 | 9.8 | 35,399 | 105,028 | 33.0 | 6/10 |
| Hybrid (BM25 + embeddings, RRF) | 8/10 | 8/10 | 4.8 | 17,796 | 43,130 | 22.1 | 8/10 |
| Wiki + hybrid search (designed after runs 1-3) | 9/10 | 7/10 | 7.5 | 33,730 | 86,227 | 26.8 | 9/10 |

**Settings:** model `anthropic/claude-sonnet-5`, temperature 0 where the provider allows it, max 8 turns, search returns up to 10 records (default 5), 1500 characters of each, no chunking (one record = one unit). as_of and the search filters (customer, after, before) applied before ranking, for both search techniques. Shipment text carries the temperature mode (frozen / refrigerated) next to the range.

**Hybrid:** embeddings `text-embedding-3-small` over the first 8,000 characters of each record; BM25 top 50 + meaning top 50 merged by reciprocal rank fusion (k = 60); reference numbers the agent passes in `exact` are pinned first only if they exist in the data (4-digit years and clock times never count); copies collapsed (attachments: same file; emails: near-identical body with identical numbers).

**Embedding token count:** 9,526,378 tokens for 36,973 records (measured, as reported by the API, 2026-10-26 10:52).

**Wiki:** customer and pickup-facility pages generated from TMS shipments per as_of date (addresses normalized); reads capped at 12,000 characters, grep at 40 lines.

## Per question

| Question | Technique | Pass | Cited | Calls | Evidence chars | Tokens | Latency s | Stopped |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| q01 | Agentic RAG (BM25) | yes | yes | 3 | 8,768 | 18,863 | 12.46 | answer |
| q01 | Direct corpus interaction (wiki) | yes | yes | 3 | 1,416 | 10,471 | 7.03 | answer |
| q01 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 4 | 17,364 | 34,318 | 14.76 | answer |
| q02 | Agentic RAG (BM25) | yes | yes | 5 | 14,023 | 30,865 | 12.63 | answer |
| q02 | Direct corpus interaction (wiki) | yes | yes | 9 | 34,097 | 118,873 | 29.21 | max_turns |
| q02 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 3 | 11,440 | 19,488 | 14.15 | answer |
| q03 | Agentic RAG (BM25) | no | no | 4 | 10,828 | 22,653 | 13.67 | answer |
| q03 | Direct corpus interaction (wiki) | yes | yes | 14 | 48,149 | 169,192 | 63.72 | max_turns |
| q03 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 3 | 7,714 | 15,646 | 17.3 | answer |
| q04 | Agentic RAG (BM25) | yes | yes | 8 | 18,878 | 59,776 | 19.11 | answer |
| q04 | Direct corpus interaction (wiki) | yes | yes | 12 | 31,361 | 131,887 | 28.53 | answer |
| q04 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 2 | 4,654 | 10,881 | 8.58 | answer |
| q05 | Agentic RAG (BM25) | no | yes | 3 | 10,064 | 17,020 | 10.55 | answer |
| q05 | Direct corpus interaction (wiki) | yes | yes | 3 | 31,744 | 49,547 | 8.28 | answer |
| q05 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 4 | 12,303 | 25,538 | 15.09 | answer |
| q06 | Agentic RAG (BM25) | no | yes | 3 | 18,440 | 20,658 | 11.89 | answer |
| q06 | Direct corpus interaction (wiki) | yes | yes | 4 | 16,777 | 30,776 | 9.23 | answer |
| q06 | Hybrid (BM25 + embeddings, RRF) | no | yes | 2 | 7,453 | 12,228 | 9.75 | answer |
| q07 | Agentic RAG (BM25) | yes | yes | 9 | 20,234 | 63,081 | 29.22 | answer |
| q07 | Direct corpus interaction (wiki) | yes | yes | 10 | 35,827 | 98,245 | 43.78 | max_turns |
| q07 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 9 | 23,460 | 84,313 | 60.93 | max_turns |
| q08 | Agentic RAG (BM25) | yes | yes | 4 | 14,841 | 27,500 | 10.49 | answer |
| q08 | Direct corpus interaction (wiki) | yes | yes | 4 | 25,250 | 30,459 | 9.42 | answer |
| q08 | Hybrid (BM25 + embeddings, RRF) | yes | no | 7 | 40,924 | 84,735 | 25.31 | answer |
| q09 | Agentic RAG (BM25) | no | no | 16 | 90,179 | 227,603 | 58.02 | max_turns |
| q09 | Direct corpus interaction (wiki) | yes | yes | 22 | 98,911 | 275,764 | 89.67 | answer |
| q09 | Hybrid (BM25 + embeddings, RRF) | no | no | 11 | 35,775 | 116,434 | 41.06 | max_turns |
| q10 | Agentic RAG (BM25) | no | no | 15 | 61,568 | 191,784 | 42.46 | max_turns |
| q10 | Direct corpus interaction (wiki) | yes | yes | 17 | 30,457 | 135,062 | 40.79 | max_turns |
| q10 | Hybrid (BM25 + embeddings, RRF) | yes | yes | 3 | 16,875 | 27,720 | 13.57 | answer |
| q01 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 4 | 17,160 | 24,492 | 13.1 | answer |
| q02 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 2 | 3,539 | 12,295 | 9.61 | answer |
| q03 | Wiki + hybrid search (designed after runs 1-3) | no | no | 5 | 18,637 | 53,479 | 14.03 | answer |
| q04 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 6 | 35,069 | 58,890 | 17.34 | answer |
| q05 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 6 | 41,576 | 108,720 | 16.24 | answer |
| q06 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 7 | 20,340 | 52,146 | 15.74 | answer |
| q07 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 8 | 33,281 | 75,536 | 27.05 | answer |
| q08 | Wiki + hybrid search (designed after runs 1-3) | yes | yes | 10 | 37,004 | 111,216 | 22.96 | max_turns |
| q09 | Wiki + hybrid search (designed after runs 1-3) | yes | no | 19 | 93,445 | 229,777 | 95.12 | answer |
| q10 | Wiki + hybrid search (designed after runs 1-3) | yes | no | 8 | 37,250 | 135,717 | 37.15 | answer |
