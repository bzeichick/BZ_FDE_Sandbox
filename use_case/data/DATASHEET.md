# Datasheet

<!-- Written in TC2, alongside your synthetic data. This file is committed; the
     data itself is not. -->

**Kind:** prototyping data. Every expected output was written by the generator; none has been checked by the order desk.

## What this data is

**Generated on:** 2026-10-16
**Generated from:** the order-intake schema in `CHARTER.md` plus 3 of the goldens in `use_case/evals/golden.jsonl` shown as examples, with instructions to invent all names, IDs and companies and to follow each combination's profile literally. The goldens are fictionalized versions of real orders (see the outward check below).
**Generator:** `anthropic/claude-sonnet-5`, called through LiteLLM. One prompt per axis combination, 3 rows per prompt, provider-default sampler settings, no seed sent to the model. Combinations were shuffled with `random.Random(0)` and the first 18 of 576 were run.
**Rows:** 50 in `synthetic_v1.jsonl` (51 parsed → 0 dropped as near-duplicates at 0.7 → 50 schema-valid, 1 rejected for a missing string field). Each row keeps the `axes` that produced it.

## Variation axes
Two runs: ENTERABLE (540 combinations, all five axes crossed) and ROUTE_TO_PERSON (12 combinations, arrival × reason). 
Routing is what the second run tests; field extraction is covered by the first.

| Axis | Values |
| --- | --- |
| arrival | one clean email from the shipper's usual template · a long thread of back-and-forth with the broker, with signatures and quoted replies, sometimes printed from Gmail with page headers · a short email with an attached PO or freight confirmation pasted in as text, where the order details live in the attachment |
| location_reference | full street address for pickup and delivery · pickup named only by an invented facility nickname, such as 'the north DC' · pickup implied ('our usual dock', 'same place as last time') with no address |
| request | a new order · a quote request with no price agreed yet · a quote thread where the customer accepts a rate the broker quoted · a correction later in the thread that changes the date or pallet count |
| temperature | a stated number or range, frozen or refrigerated · a mode word only ('frozen', 'REFER', 'refrigerated'), no number · no temperature stated |
| date_phrasing | explicit pickup or ready date and delivery date · flexible readiness: a relative day ('as early as Friday') or several options ('9/30 or 10/1') · a delivery deadline ('before or on 10/7') or a vague window ('week of 10/5') · the broker proposes a pickup date in the thread, and the customer confirms it or pushes back · no date given |
| reason (route-to-person run) | no pickup location given at all · a cancellation of an order sent earlier in the thread · a status update on a load that was already picked up · several shipments in one email |


<!-- Rebuild after the new run

How the rows came out, by axis:

| Asked for | Rows | What the expected output does |
| --- | --- | --- |
| No pickup location | 23 | 17 leave origin empty and ask for it; 6 keep a company or city but no street |
| Implied or nickname-only pickup | 12 | All 12 have no street address |
| Full street address | 15 | All 15 have a street address |
| Cancellation | 15 | All 15 go to a person (`needs_human`) |
| Status update on a picked-up load | 12 | All 12 go to a person |
| Correction later in the thread | 12 | All 12 are entered as orders, each with a customer question |
| New order | 11 | All 11 are entered as orders |
| Frozen, no number | 12 | 9 get the standard range and the `TEMP_STANDARD_ASSUMED` flag |

-->

## What it can validate

- The pipeline runs end to end: generate → dedupe → validate → write.
- The schema, including the fixed list of four flags, accepts well-formed rows in the shape the system returns.
- Routing: cancellations and status updates go to a person; new orders and corrections are entered.
- Missing and implied pickup locations are left empty or partial and asked about, not filled with a guessed address.
- Temperature handling for frozen with a setpoint, frozen with no number, and no temperature stated.

## What it cannot validate

- **Field accuracy.** The same model wrote each order and its expected answer, so a row shows agreement with the generator, not correctness. Only the goldens can measure accuracy.
- **Refrigerated orders.** None of the seeds is a refrigerated or fresh order, so the 18 refrigerated rows' expected outputs are the generator's guess at the rule. Only 6 use the company's standard 34–38°F range; the rest use whatever range the generated text stated. The rule that a refrigerated order with no number gets 34–38°F and a flag is untested.
- **Which value wins in a correction.** All 12 correction rows ask the customer a question, so none tests whether the system takes the latest date or pallet count from the thread.
- **Several shipments in one email.** No seed and no axis value produces one, so the charter's rule that these go to a person is untested.
- **Real frequency.** The mix of cancellations, status updates and orders is set by the axes, not by real mail. Don't read any percentage from this set as a rate.
- **Real formats.** Scanned BOLs and PDF purchase orders aren't represented, only plain email text.
- **Reproducibility.** Provider-default sampler, no seed sent to the model. Rerunning the same 18 combinations will produce different rows.

## What it must never be compared against

The ground truth is `use_case/evals/golden.jsonl` and the full eval set kept privately outside this repo. These synthetic rows are not ground truth, and a score on them must never be reported alongside or in place of a score on the goldens.

## Leakage check — outward (what left)

- [ ] No real record was used as a seed. **No.** The seeds are real orders with every identifying detail replaced: names, emails, phones, street addresses, reference numbers and dollar amounts at first; then (2026-10-16, before this run) lane cities and ZIPs, commodities, pallet/case/weight figures and dates, plus removal of the carrier's terms footer. The structure of each seed is still a real order. The earlier, less-redacted `golden.jsonl` remains in this repo's git history.
- [x] No real entity names, IDs, or identifiers appear. The leak check found no names, emails or reference numbers from the seeds; it found seed dates and the seeds' fictional street numbers, mailing-list names ("Dispatch Desk", "Order Entry") and the job title "Logistics Manager".
- [ ] No distinctive internal formats that would identify the firm. **Narrowed, not closed.** The carrier's terms footer no longer appears (0 rows, down from 31). Rows still copy the seeds' email-thread layout.
- [x] Rare categories were generated, not copied. Cancellations, status updates, corrections and missing pickup locations were all generated from the axes.

Still to do: have the client's owners review the fictionalized seeds.

## Leakage check — inward (what the eval shares with the training data)

**Are the goldens disjoint from anything the system was, or will be, tuned on?**
No — overlap: all goldens. No model weights are trained, but the system's prompt and extraction rules were revised against these exact cases. The private eval runs (v2–v11) iterated on the same source orders, and Golden #1's rules (ready date vs. pickup date, temperature as a range) were rewritten from demo feedback on it. A score on the goldens is partly a score on what the prompt was fitted to. An honest accuracy number needs held-out real orders the prompt has never been tuned on; the client's order desk is who would supply them.

**Overlap between `golden.jsonl` and this file, by the dedupe measure:** 0 of 50 rows within 0.5 of any golden.
