# Decision log

One row per architectural decision, with the option you rejected and why.

> **Week 5 asks you to defend your agent architecture against the alternatives.**
> **Week 10's handoff doc is largely this file.** Both are much easier if you
> wrote the reasoning down while you still remembered it.

A decision without a rejected alternative is not a decision, it is a default.
If you cannot name what you did not do, you did not choose.

| Week | Decision | What you rejected | Why | What would change your mind | Counter-Argument |
| --- | --- | --- | --- | --- | --- |
| 1 | Pipeline: one model call that fills responses, then schema validation | An agent that decides its own next step such as looking up customer profiles or the TMS mid-run | Every order goes through the same steps and all fields come from the order intake, the schema catches malformed output and possible outcomes are a closed list. A single model call per order keeps the cost per order fixed and predictable and gives the same path for the same input so results can be compared directly with test data | If roughly 15% of real orders end up with a question to the customer that is already captured such as address, usual pickup location, rate from lane history; then looking things up mid-order is the job, and an agent with lookup tools would be worth it. This could be measured from the questions field across trial orders | The order text alone often isn't enough because real orders use facility names instead of addresses or rely on a customer's typical pickup location. An agent that could lookup profiles, addresses, load history could fill it in itself with fewer questions back to the customer |
| 1 | Don't ask the customer for a missing delivery date, but flag it to be scheduled | Asking every customer | Matches how the order desk actually works by scheduling for the customer and advising them | If receivers start rejecting deliveries because of real deadlines that weren't communicated | Some customers' receivers have hard deadlines that only the customer knows |
| 3 | <!-- retrieval approach --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 5 | <!-- agent architecture --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 6 | <!-- guardrail level --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 7 | <!-- memory type --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 8 | <!-- model --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |

---

The last column is the one people skip and the one clients ask about. "We chose
dense retrieval; we would switch to hybrid if exact-match queries went above ~20%
of traffic" is an engineering position. "We chose dense retrieval" is a
preference.
