# Datasheet



**Kind:** prototyping data. Every expected output was written by the generator; none has been checked by the order desk.

## What this data is

**Generated on:** 2026-10-19 (full run; earlier smoke tests discarded)
**Generated from:** the order-intake schema in `CHARTER.md`, plus 2 of the 6 goldens in `use_case/evals/golden.jsonl` shown per prompt, chosen to match the row's arrival format (clean email → goldens #3, #2; long thread → #1, #5; PO attached → #6, #3). The goldens are fictionalized versions of real orders (see the outward check below). Prompt rules: invent all names, IDs, companies and addresses; follow the profile literally; the profile beats the examples; label by the charter's rules.
**Generator:** `anthropic/claude-sonnet-5` via LiteLLM, direct to Anthropic's API. One prompt per axis combination, 1 row per prompt. Provider-default sampler and reasoning (the API rejected a temperature setting; no seed sent). `max_tokens` 16000, one retry for a combination that returns nothing. Combinations shuffled with `random.Random(0)`, route-to-person combinations run first.
**Rows:** 531 in `synthetic_v1.jsonl` (551 schema-valid, minus 20 rows removed after reading)

| Count | Value |
| --- | --- |
| Combinations | 552 (540 enterable + 12 route-to-person) |
| Generated | 553 (one correction combination returned 2 rows) |
| After dedupe (character 4-gram Jaccard 0.7 on the input) | 553 — 0 dropped |
| Schema-valid | 551 — 2 rejected: for "no temperature stated" profiles the generator invented non-reefer modes ("ambient", "dry"), which US Perishables doesn't move |
| Dead combinations | 0 — 2 replies were unparseable on the first attempt; both combinations recovered on retry |
| Removed after reading 50 rows | 20 - see "What I removed" below | 
| **Final** | **531** | 

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

## How the rows came out, by axis:
| Asked for | Rows | What the expected output does |
| --- | --- | --- |
| Route to person (all 4 reasons) | 12 | 12 routed to a person |
| Full street address | 176 | 176 have a pickup street; 0 ask about origin |
| Nickname-only pickup | 171 | 0 have a pickup street; 141 ask about origin |
| Implied pickup | 172 | 0 have a pickup street; 165 ask about origin |
| New order | 131 | 21 have a rate |
| Quote request, no price agreed | 131 | 0 have a rate |
| Quote accepted in thread | 125 | 125 have a rate |
| Correction later in thread | 132 | 0 ask about pallets |
| Stated temp number or range | 177 | 154 refrigerated, 23 frozen; 0 flagged |
| Mode word only | 170 | 103 refrigerated, 67 frozen; 167 flagged TEMP_STANDARD_ASSUMED |
| No temperature stated | 172 | 172 ask about temperature |
| Explicit dates | 102 | 67 ready date; 40 firm pickup date |
| Flexible readiness | 104 | 104 ready date; 0 firm pickup date |
| Deadline or window | 102 | 64 ready date; 21 firm pickup date; 18 ask for a ready date |
| Broker-proposed pickup | 104 | 57 firm pickup (confirmed); 48 ready date (pushed back) |
| No date given | 107 | 107 ask for a ready date |

## What it can validate

- The pipeline runs end to end: generate → dedupe → validate → write.
- The schema, including the fixed list of four flags, accepts well-formed rows in the shape the system returns.
- Routing: cancellations and status updates go to a person; new orders and corrections are entered; handles emails with multi-shipments and orders with no pickup info thinly (3 rows each).
- Missing and implied pickup locations are left empty or partial and asked about in 306 of 343 rows, not filled with a guessed address.
- Temperature handling for refrigerated, frozen with a setpoint, frozen with no number, and no temperature stated.

## What it cannot validate

- **Field accuracy.** The same model wrote each order and its expected answer, so a row shows agreement with the generator, not correctness. Only the goldens can measure accuracy.
- **Real frequency.** The mix of cancellations, status updates and orders is set by the axes, not by real mail. Don't read any percentage from this set as a rate.
- **Frozen/Refrigerated skew.** In the current dataset, stated temperatures are 154 refrigerated to 23 frozen, and mode words 103 to 67, while real freight for this broker is mostly frozen.
- **Customer Profiles.** Labels assume text-only extraction and don't use customer profiles, and nickname and implied rows will eventually need re-labelling.
- **Real formats.** Scanned BOLs, images, and PDFs that need text extraction aren’t represented; attachments appear only as clean pasted text.
- **Reproducibility.** Provider-default sampler, no seed sent to the model. Rerunning the full dataset will produce different rows.
- **Repeated Invented Details.** The current model used the same PO (BH4471) in 29 rows, the same contact (Dana) in 163 rows, and send times (8-9am) in 358.
- **Answer-key labels for two rules.** About a third of the 61 remaining firm-pickup rows may repeat the demo error, and 37 nickname or implied rows have no origin question. Don’t score the system against these labels until they’re fixed.

## What it must never be compared against

The ground truth is `use_case/evals/golden.jsonl` and the full eval set kept privately outside this repo. These synthetic rows are not ground truth, and a score on them must never be reported alongside or in place of a score on the goldens.

## Leakage check — outward (what left)

- [ ] No real record was used as a seed. **No.** The seeds are real orders with every identifying detail replaced: names, emails, phones, street addresses, reference numbers and dollar amounts at first; then (2026-10-16, before this run) lane cities and ZIPs, commodities, pallet/case/weight figures and dates, plus removal of the carrier's terms footer. The structure of each seed is still a real order. The earlier, less-redacted `golden.jsonl` remains in this repo's git history.
- [x] No real entity names, IDs, or identifiers appear. Read 50 rows. No real names, emails or IDs. Removed 8 rows reusing the goldens’ stand-in customer names. The broker stand-in (‘coastlinecold’, 25 rows) and mailing-list names (‘Order Entry’, ‘Dispatch Desk’) remain: fictional, kept for realism.
- [ ] No distinctive internal formats that would identify the firm. **Narrowed, not closed.** No terms footer in any row. Rows still copy the seeds’ email-thread and PO layouts.
- [x] Rare categories were generated, not copied. Cancellations, status updates, corrections and missing pickup locations were all generated from the axes.

Still to do: have the client's owners review the fictionalized seeds.

### What I removed after reading 50 rows (20 of 50)

I read 50 rows: all 12 declines, rows the automated checks flagged, a sample of firm-pickup and no-origin-question rows, and 11 at random. Removed:

- **Seed customer names (8):** rows reusing the goldens' stand-in customer names (Tidewater ×2, Sunridge ×2, Northstar ×3, Harbor Lane ×1). Fictional, but they stand in for real accounts.
- **Ready or requested date entered as a firm pickup — the demo error (3):** "ready Thursday 11/5"; "Requested Pickup Date"; a customer asking for "Pickup Friday the 6th".
- **Nickname or implied pickup with no origin question (5):** origin left without a street and never asked about.
- **Text contradicts its profile (3):** two "implied/nickname" rows whose text contains a full address; one "no temperature" row whose text says "Frozen Mixed Berries".
- **No temperature and no question (1).**

Kept with notes (6): three "REFER" rows labelled refrigerated correctly but missing TEMP_STANDARD_ASSUMED; one vague delivery window missing DELIVERY_TO_BE_SCHEDULED; one row with both ready and pickup dates set; one refrigerated-snack-bar row (kept — such products can need refrigeration).

**Not fixed, estimated from the sample:** 3 of the 8 firm-pickup rows I read had the demo error, so roughly a third of the remaining 61 firm-pickup rows (explicit and deadline dates) may too. 37 nickname or implied rows still have no origin question. Both are known label defects in rows I didn't read.

## Leakage check — inward (what the eval shares with the training data)

**Are the goldens disjoint from anything the system was, or will be, tuned on?**
No — overlap: all goldens. No model weights are trained, but the system's prompt and extraction rules were revised against these exact cases. The private eval runs (v2–v11) iterated on the same source orders, and Golden #1's rules (ready date vs. pickup date, temperature as a range) were rewritten from demo feedback on it. A score on the goldens is partly a score on what the prompt was fitted to. An honest accuracy number needs held-out real orders the prompt has never been tuned on; the client's order desk is who would supply them.

**Overlap between `golden.jsonl` and this file, by the dedupe measure:** 0 of 531 rows within 0.5 of any golden (closest: 0.37, measured).
