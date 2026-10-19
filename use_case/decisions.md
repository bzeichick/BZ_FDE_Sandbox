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
| 1 | Record the customer's date as a ready date; leave pickup to be scheduled, and record temperature as a range | Treating the customer's "ready Friday" or requested date as the pickup date, and temperature as a single max | Demo feedback: the company consolidates pickups on its own scheduled runs, so a ready date entered as a pickup date would mislead whoever reads the TMS; frozen is a 0 to -10 range, not one number. Golden #1 was rejected on exactly this and rewritten. | If customers' ready dates turn out to be firm pickup commitments for some accounts | For some shippers the dock schedule is fixed, so their date really is the pickup date and flagging it adds work |
| 2 | Keep a measured local open-weights baseline alongside the hosted model. Same 80-token generation: local LiquidAI/LFM2.5-350M, CPU-only on MacBook Pro (Apple M_, __ GB) = 48.17 s (~1.7 tok/s); hosted anthropic/claude-sonnet-5 = 2.61 s (~31 tok/s) | Hosted-only, with no local measurement to compare against | A local model keeps order and customer data on our own hardware and gives us the full logits and our own sampler whereas the hosted provider rejected temperature=0.7 and ran at its default. Any later move to a fine-tuned open model has to be argued against this baseline, and it is what an internal server would be sized from. Local figure is a worst case: the test loop recomputes the whole sequence each step with no KV cache | If a proper serving stack (e.g. vLLM on a GPU) brings local within ~2–3× of hosted latency at usable quality, or if shippers require that order data never leave our network | Local is ~18× slower and its output was visibly worse (repeated words, drifted off-topic); for order intake today the hosted model is the practical choice, and the local baseline only matters if data residency or sampler control becomes a hard requirement |
| 3 | <!-- retrieval approach --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 5 | <!-- agent architecture --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 6 | <!-- guardrail level --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 7 | <!-- memory type --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |
| 8 | <!-- model --> | <!-- --> | <!-- --> | <!-- --> | <!-- --> |

---

The last column is the one people skip and the one people ask about. "We chose
dense retrieval; we would switch to hybrid if exact-match queries went above ~20%
of traffic" is an engineering position. "We chose dense retrieval" is a
preference.
