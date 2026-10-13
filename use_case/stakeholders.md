# Stakeholders

Everyone you talk to about this project, from the first "where would this even
run?" to the final readout.

> **Week 10's technical challenge is a client report to the people in this file.**
> You cannot write it later from memory. Add a row the day you have the
> conversation.

Use roles, not names. This is a public fork.

| Week | Who (role) | What you asked | What you learned | Follow-up |
| --- | --- | --- | --- | --- |
| 1 | Co-owner, freight brokerage | Where would a small internal web app run, who would sign in to it, can it call an outside AI service, and who approves it? | No company platform: it runs on the VM I administer under my consulting company's AWS account. Email is Microsoft 365 but nobody knows who holds the admin account, so sign-in is per-person passwords for the trial. OK to send orders to an outside LLM, with alternatives ready. Trial with four order-desk users. Their bar: saves time, easy to use, no mistakes. | Recover the Microsoft 365 admin; schedule the trial and demo (Step 12). |
| 1 | Co-founder (one of the trial users; the ops coordinator wasn't available) | Screen-shared demo of 5 orders; asked what's missing before he'd use it | Looks good overall. A customer's "ready Friday" is not the pickup date — pickups are scheduled around our own consolidated runs, so the app must record a ready date. Temperature should be a range (frozen 0 to -10). Questions should ask for a ready date, and for contact name, phone and email; delivery questions should ask receiving hours and whether an appointment is needed. Most valuable next: digging for missing info and drafting appointment requests. | Ask expected cost (not asked); time one manual entry; demo to the ops coordinator. |

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
