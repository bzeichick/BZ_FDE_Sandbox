# Project charter

<!--
  Fill this in during TC1 Step 4, from your Getting to Concreteness form.
  Later weeks' notebooks read this file and stop if it is still the template.
  That is on purpose.
-->

**Department:** Operations — order desk at a cold-chain freight brokerage

**Working title:** ColdLade order intake

---

## The problem

**Who has it?** One real role, not a department.

The order desk: four people (the ops coordinator does most of it; both co-founders and the sales lead cover), with part-time and offshore help planned for surges.

**What are they trying to do?**

Turn a customer's shipping request into a correct shipment in the TMS, so it can be booked with a carrier and confirmed back to the customer.

**How do they handle it today?**

Orders arrive by email (free text in the body, often with PDF attachments such as POs and freight confirmations) or through the web form on the company's site. Phone is used only for negotiation or first contact; every order is confirmed by email. Whoever is on the order desk reads the order, emails the customer back when something is missing (a PO number, a pickup location, a temperature), types the details into the TMS by hand, and replies to confirm it's entered. Web-form orders are structured but still need checking.

**What does that cost — time, money, risk, or relationships?**

- Volume: about 145 orders a month (August month-end report).
- Time: minutes per order — to be measured (timing 3 real entries).
- Who pays it: two of the four people entering orders are the co-founders, so order entry takes owner time away from sales and customers.
- Errors already visible in TMS data: placeholder appointment times, a ZIP code in a state field, duplicate records for the same facility, $0 customer charges.
- Risk: in cold-chain freight a wrong temperature or missed pickup can mean a rejected or spoiled load and a claim. For example, sometimes a client might not specify temp, and if refrigerated is assumed instead of actually needing to be frozen, this would mean the shipment would be rejected on delivery
- Growing risk: part-time and offshore help planned for surges won't know each customer's habits.

**The problem in one sentence. No solution in it.**

The four-person order desk at a small cold-chain brokerage re-types about 145 customer orders a month from email and web forms into the TMS by hand, and entry mistakes or missing customer details lead to wrong orders and failed shipments (such as a load booked at the wrong temperature), a risk that grows as part-time and offshore help is added for surges.

---

## Success

**What does the new world look like for that person?**

An order arrives and, instead of re-typing it, whoever is on the order desk pastes it in and gets the shipment details already filled in to check. Anything the customer left out (no PO number, no pickup location, no temperature) is called out as a question to send back, not quietly guessed. The co-founders stop spending their time on data entry, and a part-time or offshore helper can enter orders correctly on day one because the customer knowledge is in the system, not only in four people's heads.

**How would the firm measure it? Which numbers should move?**

- Minutes per order: measured manual time today vs. time to check a pre-filled order.
- Accuracy: share of fields correct on real orders, starting with the five golden examples.
- Invented values: zero. A blank with a question is acceptable; a wrong guess is not.
- Missing details caught before entry rather than discovered at pickup or delivery.
- Usability: the trial users can use it without me in the room.
- Later: fewer data errors in the month-end TMS report (placeholder times, $0 charges, duplicate locations).
---

## The first product

**Your solution in one sentence.**

A web page where the order desk pastes in one customer order and gets back the shipment fields ready to check, with anything missing or unclear flagged for a person instead of guessed.

**Input → Output.** Be specific enough that someone could build it wrong and you
would notice.

| | |
| --- | --- |
| **In** | The text of one customer order: the email body, with any attached PDFs (PO, freight confirmation) converted to text and added below it, plus the date the order was received. One order per request. |
| **Out** | The shipment fields: customer reference numbers (PO/SO), origin and destination (company, city, state, ZIP), ready date, pickup date, delivery date, delivery window, temperature (frozen/refrigerated with a min–max °F range), pallets, cases, weight in lb, and rate in USD. Fields come only from the order text, never from what a customer usually does. Required fields are refs, origin, destination, a ready or pickup date, temperature, pallets, cases and weight; when one is missing it is left empty and comes with a question to ask the customer. A date the customer gives for when freight is ready, or a pickup date they request, is the ready date (the earliest if several are offered); the company picks up on its own consolidated runs, so pickup date is only a firm ship date or a pickup that already happened, and otherwise pickup is flagged to be scheduled. When a date is missing, the customer is asked for a ready date, never "when should we pick up". When the order gives no delivery date, it's left empty and flagged to be scheduled rather than asked about. Dates are single days: a deadline ("on or before 10/7") is used as the delivery date, and a vague window ("week of 10/5") is kept and flagged for scheduling. Temperature is a range: frozen -10 is -10 to 0°F; if the order says frozen or refrigerated but gives no number, the company's standard range (frozen -10 to 0, refrigerated 34 to 38) is filled in and flagged to confirm. “REFER” (or “reefer”) with no other temperature word means refrigerated; “REFER (FROZEN)” means frozen. A missing rate is not a customer question; it is flagged for a rate lookup or quote. Quote requests are treated as orders: the fields are filled the same way and the missing rate is flagged. A separate needs_human flag is set when the text isn't a single new order (a status update, or several shipments) or when origin or destination can't be determined. |

---

## Decisions made later

<!--
  Amended as the cohort goes. Keep the reasoning, not just the choice — Week 5
  asks you to defend your architecture against the options you rejected, and
  Week 10's handoff doc is largely this section.
-->

| Week | Decision | Why, and what you rejected |
| --- | --- | --- |
| 3 | Retrieval approach | <!-- TC3 --> |
| 5 | Agent architecture | <!-- TC5 --> |
| 8 | Model | <!-- TC8 --> |
