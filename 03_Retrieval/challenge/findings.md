# TC3 findings log

What reading the traces showed, beyond the pass/cited score. Newest last.
Corpus and labels: production (not committed); names below are the redacted ones.

## Corpus (Step 3a)
- Email text went from ~127M to 16.9M characters by keeping only each message's new text and
  dropping Sent/Inbox duplicates. All gold records survived.
- Cutting quoted history splits meaning across records: q07's gold reply is only "Sure, that
  will be fine." What it agrees to (Wed 8/27, 1pm) is in the message before it (msg:1326).
- Attachments are 22M characters, dominated by a few giants (a 964K insurance policy, four
  368K temperature logs; median attachment 1.6K). Reads must be capped per record.

## Agentic RAG, first run (before the loop fixes)
- Score 4/10 pass, 6/10 cited. By reading, also 4/10, but not the same four:
  q04 was right but failed on wording; q10 was wrong-looking but passed on the word "quote".
- q10's label was wrong. The run surfaced two load-board tenders (msgs 159389, 159398, March
  2025) that were accepted and delivered. Both ARE in the TMS (81029, 81028) but under two other
  customers' names, so a search by customer finds nothing; only the PO/SO connects them.
  Relabelled; the clearest case of the system teaching me something about my data.
- q06 answered "every shipment picks up at [Alameda]" after reading 5 records (true for 76%).
  q05 reported the majority temperature and missed the third that ship frozen. Top-k shows a
  sample, never a distribution.
- q07 and q09 ran out of turns: 11 and 19 searches, and the desk got nothing.

## Scorer and label changes
- Decline questions are scored on the structured `declined` field, not phrasing (q04 failed
  on four different correct wordings).
- Added `must_not_contain` to catch confident wrong answers (q06 "every shipment").

## Loop changes (apply to every technique; all re-run together for the final table)
- Prompt: stop when the records answer the question; mention small differences instead of
  investigating them.
- Out of turns: one final no-tools call returns what was found, marked partial, instead of nothing.

## Direct corpus interaction (wiki), first runs
- Making the wiki: customer and pickup-facility pages generated from TMS shipments, with
  address variants merged (one facility stored 5 ways, 169 shipments). Pages are computed per
  as_of date, so they are never stale.
- q07: read_thread had the full chain by call 3. It still used all 8 turns chasing a second,
  conflicting 8/26 request (msg:120857) and two large page reads. The rescue saved the answer:
  pass + cited, partial.
- q07's answer opens "No" and concludes "matches": a contradiction the keyword score passes.
- Cost: 121K tokens for q07, versus ~24K for RAG on an exact-ID question. Every turn resends
  everything read so far, so large reads compound.

## Direct corpus interaction (wiki), full run
- Score 7/10 pass, 4/10 cited. By reading: 9/10 right (RAG first run: 4/10).
- Patterns now work: q05 "34 of 68 at 36-44F, 23 of 68 frozen"; q06 "343 of 452 (76%)" with the
  address spellings merged; q09 all 8 customers with the exact gold shipment IDs.
- But it cited page names instead of shipment IDs on q05, q06 and q09, so "cited" undercounts.
  Fixed with a prompt line (a page is a summary; cite the shipment IDs behind each number).
- q03 was right, and failed on must_not_cite for mentioning the frozen load as excluded. Label fixed.
- q10 found the Manassas load in the TMS by PO number, recorded under another customer's name.
- Cost: much more evidence than RAG (q09 read 96K characters; list_pages alone is 18K and opens
  most questions). Being right on patterns costs reads.

## Final run 1 (10/23), read by hand
| Technique | Pass | Cited | By reading | Tokens (avg) |
| --- | --- | --- | --- | --- |
| Agentic RAG | 6/10 | 7/10 | ~6/10 | 49K |
| Wiki (DCI) | 9/10 | 7/10 | ~9/10 | 93K |
| Hybrid | 6/10 | 7/10 | ~6/10 | 44K |
- Wiki won exactly the shapes predicted: patterns (q05, q06), sets (q09), thread meaning (q07),
  at about twice the tokens and 50% more latency.
- Meaning-search added almost nothing: hybrid = RAG on pass. It fixed q03 through the filters and
  the temperature word (corpus/tool fixes), and lost q07 (concluded the superseded 8/26 appointment:
  its pin matched ~15 records with the PO and the shipment didn't make the top 5).
- RAG gave shipment 83124 a temperature it doesn't have (q03).
- Embedding token count: 9,522,895 (measured), ~$0.19.

## Label review after final run 1 (applied to all techniques, then re-run)
- q06: pass now = main site + at least one alternate. Reason: the desk acts on "there is more than
  one site" (ColdLade's rule: never default to the majority location), not the full list of streets.
- q10: each load may be proven by its TMS record or its accepted tender. Reason: the TMS records
  carry other customers' names; the tender is the record that says who tendered it.
- q10: must_not_cite now lists all 11 pickups at the unrelated Richmond cold storage. The wiki cited
  82612 as this customer's load; the emails show it's another customer's (load 170032, delivered to
  their Portland DC) with the broker itself recorded as customer. Third mis-recorded customer found.
- Citation rule: a wiki page may be cited only with 3+ shipment IDs beside it, enforced by one
  reply in the loop (it can only trigger for the wiki).

## Final run 2 (after the label review)
| Technique | Pass | Cited | Tokens (avg) |
| --- | --- | --- | --- |
| Agentic RAG	| 6/10 | 8/10 | 49K |
| Wiki (DCI) | 9/10 | 9/10 | 100K |
| Hybrid | 6/10 | 8/10 | 47K |

- The page-citation check worked: the wiki's q06 and q09 now cite shipment IDs (cited 7 -> 9).
- Run-to-run variation: hybrid flipped on q03 and q05, the wiki on q10, with identical code and
  labels. With 10 questions, a difference of one question is noise; both runs are reported.
- Hybrid's q05 passed on the word "frozen" but said "at least one load" (it's a third): wrong by
  reading. The wiki's q10 decided the unrelated Richmond cold storage is this customer's site.

## Data-quality finding: temperatures the parser missed
- Two techniques kept calling 83124 a 38F load and I kept marking it wrong. They were right: its
  temperature field is empty, but its freight description says "Refrigerated 38".
- Across all 2,636 TMS shipments, 363 had no parsed temperature and 303 of those state one in the
  description ("Frozen, -10 to 0" 207, "Chilled, 34 to 44 F" 24, "Refrigerated 38" 20...). The
  rate-confirmation parser reads only one way of writing a range.
- Fixed in corpus.py with a fallback that reads the description (and says so in the record):
  "no temperature on record" went from 363 shipments to 5. This was hiding inside the wiki's
  pattern pages (one customer showed 77% "no temperature"). ColdLade's parser needs the same fix.
- q03 relabelled to five loads. Embeddings rebuilt; the embedding file now stores a fingerprint of
  the embedded text, so a corpus change can't silently leave stale vectors.

## Final run 3 (after the temperature fix; the submitted table)
| Technique | Pass | Cited | Tokens (avg) | Latency (avg) |
| --- | --- | --- | --- | --- |
| Agentic RAG | 5/10 | 7/10 | 68K | 22 s |
| Wiki (DCI) | 10/10 | 10/10 | 105K | 33 s |
| Hybrid | 8/10 | 8/10 | 43K | 22 s |
- Across three final runs: wiki 9, 9, 10; hybrid 6, 6, 8; RAG 6, 6, 5 (pass).
- By reading: wiki 10/10 (q03 now includes 83124; q10 both loads and both tenders); hybrid ~7/10
  (q05 "one load frozen" passes on the keyword but is wrong for the third run running; q06 one site;
  q09 2 of 8); RAG ~5/10.
- Wiki cost: ~2.4x hybrid's tokens and +50% latency; 4 of 10 answers came from the out-of-turns rescue.
- Embedding token count after the corpus fix: 9,526,378 (measured).
- The biggest score movers were data fixes (email cleaning, the temperature fallback, label
  corrections), not ranking techniques.

## Technique 4: wiki + hybrid search (designed after runs 1-3, so it had an advantage the others didn't)
- Score 9/10 pass, 7/10 cited; 86K tokens (wiki 105K), 27 s (wiki 33 s), 9/10 finished on their own.
- By reading ~7/10. With a search tool available, the model took the shortcut: q03 answered from a
  search (4 of 5 loads) without reading the customer page; q10 stopped after one of the two loads.
- q09 named all 8 customers, then excluded two because "2026-07-09 falls outside the window that
  starts 2026-04-19" -- a date-arithmetic error that the keyword score passes. Reasoning, not retrieval.
- q09 still cost 230K tokens (18 page reads).
- Conclusion: adding search makes the wiki ~18% cheaper and less accurate. Not shipped.

## The endpoint (Step 4): trying it, after measurement
- Shipped technique: the wiki (direct corpus interaction), behind `answer_from_history` and a
  question page at /history. The page shows what the records cover, worked out from the data.
- First try, status of SO-073902 (q02) "as of today": right facts, but it read the missing POD as
  "not delivered", because the model didn't know where the records end. Fix: when the as-of date is
  past where records stop, the prompt says where each kind stops (never applies to the labelled
  questions, so the measured prompt is unchanged).
- Docker check (synthetic data, no production files in the image): runs, answers cite syn: records,
  the page labels it demo data. It exposed a read_thread bug: emails with no thread ID (all synthetic
  ones) were grouped into one "thread" of 531 orders. Fixed: an unthreaded email is its own thread.
  Production unaffected (every production email has a thread ID), so no re-measure.
- On demo data some answers still hit the turn limit: with no shipments there are no customer or
  facility pages, so the model spends turns confirming nothing else exists.

## Live mail (the server's weekday pull)
- The endpoint now also reads the business email the server saves every weekday (backfill +
  intake .eml files): +1,232 emails after de-duplicating against the export (569 after 10/19),
  linked into existing threads by conversation ID. measure.py strips it, so the measured corpus
  stays the frozen snapshot.
- Emails now run to the latest pull; TMS shipments still stop at 10/16, because they come from
  carrier rate confirmations and the pull skips the broker's own carrier tenders. The TMS export
  (Week 5) is what closes that gap. Attachments in live mail aren't read yet.
- 9 of 11 test questions right, including several only live mail can answer (a cancelled tender,
  a postponed quote, POs scheduled for November).
- Two misses, one cause: grep returned the first 40 matches in corpus order (old export first, live
  mail last), so broad patterns (a customer name, "2026-10-21") never reached recent mail. "Newest" was
  always last; live mail exposed it.
- Fixes: grep searches newest first; prompt rule "when records disagree, the most recent wins, and
  say what it replaced". Both change the measured technique, so the wiki was re-measured: 9/10 pass,
  8/10 cited (run 3: 10/10, 10/10), within the run-to-run spread (9, 9, 10, 9). q10 took the
  Richmond cold-storage trap again (2 of 4 runs: a wiki-specific weak spot, unrelated to the
  fixes); q09 named all 8 but said "six"; q07 opened "No" over the 30-minute difference. Kept both.
- Re-asked: the Brightloaf 10/21 order is now found (a frozen PO, confirmed the same day). Fix worked.
- Still wrong: SO-073902 gives 10/22 06:00 (cooler dock). The final change, to 10/21 08:00 at the
  frozen dock, is in a 10/16 email that cites only the customer PO, not the SO the question used,
  and the TMS record (10/21 07:30) was set aside. Multi-reference hop: the later update uses a
  different reference number than the question. A Week 4 debugging case.
- Maintenance: the endpoint docstring's coverage dates are fixed text; when the TMS feed is live,
  update them or let /coverage be the source.

## Is email the right source? (after the endpoint)
- Of the 10 labelled questions, 6-7 are better answered from the TMS than from email: q01/q02
  (booked? status), q03/q05/q06/q09 (counts over structured fields), q04 (the TMS holds the
  customer charge; email-only can just decline). q07 needs both (booking + receiver confirmation).
  q08 (dock hours) and q10 (loads under other customers' names) need email.
- Email covers what the TMS can't: anything before or outside a booking (quotes, tenders, orders
  not yet entered, cancellations), who agreed to what, and checking the TMS against what was
  agreed. This week alone found three loads under the wrong customer, 303 shipments with a missed
  temperature, and appointment times that differ between the TMS and the confirmation emails.
- So the app should be "TMS first, email for what the TMS doesn't know". The endpoint, contract,
  wiki pages and loop stay; the TMS export becomes the main source (the Week 5 exact-reference tool,
  and profile pages built from TMS records instead of parsed rate confirmations).
- Open question before Week 5: how much history the TMS can export (the current lookup export is
  ~138 recent rows).

  ## User-session questions, scored (Step 6)
- The 10 questions from the two sessions (u01-u05 sales, u06-u10 operations) are labelled against
  the production corpus plus live mail frozen at 10/27 15:30 UTC (`measure.py --live`, wiki only,
  [results_users.md](results_users.md)). Kept apart from the main 10: 7 of them need mail received
  after the TMS shipment records stop (10/16), and the main run must not change as mail arrives.
- 8/10 pass, 9/10 cited. u03: the question names the wrong state for the returned pallet; the agent
  took it literally, found no delivery there among that customer's 10/9 shipments, and declined
  without searching the PO's "pallet discrepancy" emails (it answered correctly in the live session,
  so this varies run to run). u06: the order details were right, but it read the 10/27 "ready 11/2?"
  email as a re-confirmation and kept the 10/26 pickup. The reviewer's "wrong" holds, but because
  the pickup moved, not because the TMS records stop.
- Two of my first labels were wrong and the app was right. u09: the customer quote sits in an email
  that names only the quote number, not the order number I searched for. u02: the claim was on the
  original load, not the return-trip tender I labelled. Lesson: label by reading the thread, not by
  searching for the reference the user typed.
- Operations' "what did you want to ask" (double POs) was already in her questions: one PO is on a
  9/1 shipment and on the new 10/27 order. u08 fails if it cites the 9/1 shipment; it passed.
- Another TMS-vs-email mismatch: one of u05's loads is entered in the TMS as refrigerated 30-34 F,
  but the freight and the email thread say frozen.
- For Week 4: when one detail of a question matches nothing, search on the others before declining
  (u03); every dollar figure says whose rate it is; tell "ran out of turns" apart from "may be
  incomplete", since 5 of the 7 turn-limit answers were correct.