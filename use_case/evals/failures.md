# Failure taxonomy: order entry (Week 4, Step 1)

**What was read:** 50 real customer orders from the broker's mailbox (Oct 2024 – Oct 2026), picked
round-robin across 13 customers so no single customer dominates, run through
`draft_shipment_from_order` on `anthropic/claude-opus-5-5`. Each draft was read against the order and
against what ops actually booked in the TMS.

**Pass rule:** an ops reviewer could approve the draft and let the agent enter it, changing nothing.
Every filled TMS field correct (nothing wrong or invented), nothing the order stated missed, every gap
needed before booking left blank and asked or flagged, `needs_human` true exactly when a person must act.
Open customer questions can still pass.

**Result: 18 of 50 failed (36%); 32 passed.**

## Failures, ranked (each trace counted once, by its main cause)

| # | Failure | Count | Traces | Checkable without a model? |
|---|---|---|---|---|
| 1 | Temperature range built from a single number: a setpoint like "chilled @ 32" or "frozen at zero degree" entered as 32–32 or 0–0 instead of the mode's standard range | 5 | 7, 10, 20, 28, 46 | Yes: min ≠ max unless the order states an explicit range |
| 2 | Required gap left silent: both stop zips missing, neither asked nor flagged (all one customer's trucking form) | 3 | 9, 22, 35 | Yes: every empty booking field appears in questions or flags |
| 3 | Temperature value that isn't in the order: one copied from the order form's example text ("0º to 10º"), one with an unsupported lower bound | 2 | 23, 47 | Partly: every number in the temperature fields appears in the order or is the mode's standard |
| 4 | An update or revision drafted as a new order: "PO has been updated", and a revised quantity still pending the customer's confirmation, both drafted as new confirmed orders with no escalation (duplicate / wrong-quantity risk) | 2 | 19, 24 | No: needs a judgement about what the email is |
| 5 | Escalation wrong: once over (two POs ops booked as one load), once under (a "please accept this tender" message that isn't an order) | 2 | 38, 39 | Yes against a label: `needs_human` exact match |
| 6 | Stale or conflicting document data used without a flag: a template's leftover dates, a leftover reference number from a reused form | 2 | 6, 41 | No |
| 7 | Pallet spots not captured: "60 PALLETS 30 SPOTS" entered as 60; ops books the 30 spots | 1 | 4 | Yes: spots stated in the order → `pallet_spots` filled |
| 8 | Customer's misspelled city copied into the TMS | 1 | 21 | Partly: city/zip agree |

Temperature (groups 1 and 3) is **7 of the 18 failures**: the biggest single area.
Secondary in two of these traces: the standard minimum temperature left blank (6, 38).

## What the scoring itself showed

- **The tool is inconsistent on identical input.** "SHIP FROZEN AT ZERO DEGREE" became −10 to 0 three times and 0 to 0 once.
- **Ops is inconsistent too.** Single-number temperatures were booked as 36/36, 0/0, 38/38 and 32–38. Whether a setpoint should become the standard range is a call two people at the broker would make differently. My rule follows my stated design (setpoint ≠ range); this needs settling with the ops lead before it's scored as a hard rule. The co-owner settled it for chilled beef (33–38, suggested back to the customer), and said that it’s commodity-dependent for everything else.
- **My own criteria moved.** Six traces needed a second decision because the tool did exactly what ops had done (or the reverse). Those were settled explicitly: 4, 10, 20, 21 fail; 36, 48 pass.
- **Appointments are almost never flagged**, even when the order says "appointment required". Not counted as failures: appointments are the dispatch step, not order entry.
- **The update failure is real, and noise is what triggers it.** Trace 19 ("PO has been updated") failed 3 of 3 when re-run on the real email (Opus, 10/30). A cleaned-up version of the same message, written as an S8 scenario, passed every time: the signature, warehouse rules and bill-of-lading boilerplate bury the one line that matters. Test cases should come from real traces, not hand-written versions of them.

## What these led to

- **Group 7:** added `pallet_spots` to the endpoint's contract and rules. Trace 4's order now gives pallets 60, spots 30.
- **Customer profiles** (planned as the Week 4 experiment, measured against the baseline): expected to help the thin load tenders and per-customer temperature defaults. They will **not** fix group 2 or the origin of lists that never name a pickup, by design.
- **Groups 1–3** are the first model-free scorers to write.
