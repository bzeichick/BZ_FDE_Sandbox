# Stakeholders

Everyone you talk to about this project, from the first "where would this even
run?" to the final readout.

> **Week 10's technical challenge is a report to the people in this file.**
> You cannot write it later from memory. Add a row the day you have the
> conversation.

Use roles, not names. This is a public repo.

| Week | Who (role) | What you asked | What you learned | Follow-up |
| --- | --- | --- | --- | --- |
| 1 | Co-owner, freight brokerage | Where would a small internal web app run, who would sign in to it, can it call an outside AI service, and who approves it? | No company platform: it runs on the VM I administer under my consulting company's AWS account. Email is Microsoft 365 but nobody knows who holds the admin account, so sign-in is per-person passwords for the trial. OK to send orders to an outside LLM, with alternatives ready. Trial with four order-desk users. Their bar: saves time, easy to use, no mistakes. | Recover the Microsoft 365 admin; schedule the trial and demo (Step 12). |
| 1 | Co-founder (one of the trial users; the ops coordinator wasn't available) | Screen-shared demo of 5 orders; asked what's missing before he'd use it | Looks good overall. A customer's "ready Friday" is not the pickup date — pickups are scheduled around our own consolidated runs, so the app must record a ready date. Temperature should be a range (frozen 0 to -10). Questions should ask for a ready date, and for contact name, phone and email; delivery questions should ask receiving hours and whether an appointment is needed. Most valuable next: digging for missing info and drafting appointment requests. | Ask expected cost (not asked); time one manual entry; demo to the ops coordinator. |
| 2 | Sales Director, freight brokerage (forwarded by the co-founder) | Sent 20 synthetic orders, each with what the tool would enter in the TMS, plus three questions: which would never happen, what comes in that isn't here, what would worry you if public. | Replied 10/20 in writing with a verdict per order, then by phone. Written: 17 "Good". Order 1: "Missing pick up address." (agrees with the tool sending it to a person). Order 2: "New rate for the 5 pallets, instead of the 6-pallet rate." (a correction that changes the pallet count makes an earlier rate stale; it has to be re-quoted). Order 4: "Rate is needed." (agrees with the rate-lookup flag). By phone: no types of orders missing, and nothing in the fake data worried him. Marked order 11 (frozen product with the reefer at 36 °F) and order 13 (carton stock, not food) "Good", so the review checked the tool's entries against each email rather than whether the orders are realistic. | Add the re-quote rule to the charter and the generation prompt; ask whether frozen product at 36 °F or non-food loads ever happen. |
| 2 | Operations, freight brokerage (enters orders and handles other operations work) | Same 20 orders and three questions. | Replied 10/20 in writing, as triage rather than a realism check: sorted each order into "Potential Order" (quote stage — no rate quoted or approved) or "Valid Order" (rate approved, the "go signal"), and named what's needed before a rate can be quoted: pickup date, pickup location, temperature requirement and type of commodity. Every order "is stated as 'Dry' or 'Temp Controlled'" (order 16) — dry freight is moved. Realism: a separate PO for each delivery location (order 11); a carrier "would not confirm rate to shipper, unless the lane is not a usual lane" (order 4). For "usual dock", "historical order can be used for the PU Location" (order 2). Prefers the shipper state the temperature range (order 18). | Add "dry" to temperature mode (schema, prompt, app) in Week 3; decide whether "ambient" = dry; consider an order-status field (potential vs. valid) and a commodity field; ask whether a flagged standard temperature range is acceptable or should always be a question. |

---

## Not everyone is an infrastructure contact

The useful list is wider than it first looks, and Week 10's report goes to all of
them:

- **The person with the problem** — the one from your charter. Have you shown
  them anything yet?
- **Whoever owns the data** you would need.
- **Whoever runs the platform** your app would deploy onto.
- **Whoever approves** a deployment, a spend, or a vendor.
- **Your own manager**, who will be asked whether this was worth the ten weeks.

If a week goes by with no conversation, add a row saying so and why. A visible
gap is more useful than a silent one.
