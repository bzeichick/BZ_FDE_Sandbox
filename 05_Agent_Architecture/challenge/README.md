<div align="center">
  <img
    src="https://github.com/AI-Maker-Space/LLM-Dev-101/assets/37101144/d1343317-fa2f-41e1-8af1-1dbb18399719"
    width="200"
    alt="AI Makerspace logo"
  />
  <h1>Technical Challenge 5</h1>
  <p><strong>The refined demo, and an architecture you can defend with a second implementation you measured.</strong></p>
</div>

> **What changed after critique.** The TC4 room said the escalation score hid the misses (0.75 accuracy hid 4 of 9 orders missed), that duplicates should be checked in code against the TMS before the model's judgment, and that 20 cases can't be told apart from guessing. This week escalation is reported as misses and gated (any increase fails). A code check against loads already in the TMS, before and after one model call, cut misses from 4 of 9 to 1 of 9; the one left, a load-board tender, is shown in the demo on purpose. One real case from shadow intake was added (a PO rewritten by a dock system). Still open: partial loads. The refined demo went to the co-owner, who called the daily agent-vs-TMS email "the first thing to look at," and named the worst case: wrong information sending the team on "a wild goose chase." My write-up for this challenge starts at [Step 2](#step-2--the-second-way-and-the-closest-reject).

**Loom (five minutes or less):** [TC5 demo](https://www.loom.com/share/e32d28641d014b59b45f4e1ac75546b1)

---

## Overview

> **Read first:** [`use_case/decisions.md`](../../use_case/decisions.md). This
> challenge fills in its architecture row. It starts with the questions from
> Session 9 that you could not answer.

Session 9 put your demo in front of a tough room, and one of its questions
was *"what did you reject?"* This challenge gets you a real answer. You
**build an alternative and measure it against what you have.**

Weeks 1–4 gave you an endpoint, data, retrieval and a number. This week your
architecture becomes a decision. A design review asks one question, and
"we use MCP" does not answer it:

> **"Why this way, and what would make you switch?"**

The second implementation is a few dozen lines. **The measurement and the
switch condition are the assignment.**

> 💡 **You already know enough to be dangerous!** In Session 10 you built the
> same capability six ways: a tool, a skill, a subagent, an MCP server, Code
> Mode, and UTCP. You put a counter on five of them that separates model calls
> from capability calls. You watched the tool loop's token cost climb with
> payload size while Code Mode stayed flat. Now you run that comparison on
> your own endpoint, at your own response size.

<table>
  <tr>
    <td width="120"><strong>Outcome</strong></td>
    <td>A second implementation of your endpoint, with both versions measured on model calls, capability calls, latency and tokens at your real response size. An architecture row in <code>use_case/decisions.md</code> with the closest reject and a switch condition. A refined five-minute demo that answers what the room asked.</td>
  </tr>
  <tr>
    <td><strong>Tools</strong></td>
    <td>LiteLLM, Gradio, and the <code>Meter</code> and capability counter from Session 10 (middleware on a FastMCP server, or the deep dive's counting wrapper). <code>fastmcp</code> or <code>mcp</code> 2.0+ only if the second way is an MCP server. Nothing else new.</td>
  </tr>
  <tr>
    <td><strong>Due</strong></td>
    <td>End of the week. Post your repo link in the Maven Community.</td>
  </tr>
  <tr>
    <td><strong>Before you start</strong></td>
    <td>Your TC3 endpoint running, your TC4 numbers, and the questions you wrote down during Session 9. If you did not write them down, Step 1 tells you what to do instead.</td>
  </tr>
</table>

---

<!-- deliverables:start -->
## 🏗️ Build | 🚢 Ship | 📤 Share

Three escalating bars. **Build** means it runs for you. **Ship** means someone
else can run it. **Share** means someone who is not you has an opinion about it.

### 🏗️ Build

A second implementation of your endpoint, in the way you judged second best,
measured against the first at your real response size. That measurement is
what lets you defend the decision.

Four questions are asked inside the Session 10 notebook as you work through
it. *They are not submitted and not graded.* They help you work out what the
challenge is going to ask you for.

| # | Question | Asked in |
| :---: | --- | --- |
| 1 | What your endpoint's dispatcher does today on a tool name it does not have, and which of the five failure rows a user of your app would meet first | S10 |
| 2 | Who outside your codebase would need to discover your capability in the next year (a named client), and what MCP buys you if the answer is nobody | S10 |
| 3 | How many bytes your endpoint really returns per call, how many calls a request needs, and where that puts you on the tool-loop slope | S10 |
| 4 | Which of the six ordering questions decides it for *your* endpoint, and the condition under which you would switch | S10 |

> **Jumping to one.** Open the notebook, then add the anchor to your browser's
> address bar, for example `#discuss-question-3`. It works once the notebook has finished loading.

### 🚢 Ship

This is the graded part. Every item comes from a numbered step in the technical
challenge, which has the full detail.

- [ ] **The room's questions written down** in `use_case/decisions.md`: the two you will fix, and the one you could not answer
- [ ] **A second implementation of your endpoint**, in the way you judged second best, running
- [ ] **Both implementations measured**: model calls, **capability calls**, latency and tokens, on the same two requests
- [ ] **The token measurement repeated at your endpoint's real response size**, with the size in bytes recorded
- [ ] `use_case/decisions.md` has the architecture row: decision, closest reject, why in terms of the six questions, and **switch condition**
- [ ] It still runs in Docker

### 📤 Share

- [ ] **The refined demo, shown to a real stakeholder**, with what changed after critique and what they asked, recorded in your own words. Graded
- [ ] **What you would swap to run this at work**: data, model or endpoint, and the approval you would need, as three lines in your README
- [ ] Your repo link posted in [our community on Maven](https://bit.ly/fde1-maven-community)
- [ ] Comments on at least two other students' submissions, after the deadline
<!-- deliverables:end -->

---

## 📖 Official documentation

Everything this challenge uses, from the people who maintain it.

| Tool | What you use it for here | Docs |
| --- | --- | --- |
| LiteLLM | `completion(tools=...)`, the model loop in every way that uses one | [docs.litellm.ai — function calling](https://docs.litellm.ai/docs/completion/function_call) |
| Gradio | the endpoint under test, and exposing it as an MCP server if that is your second way | [gradio.app — building an MCP server](https://www.gradio.app/guides/building-mcp-server-with-gradio) |
| MCP | the protocol, if the second way is a server something else has to discover | [modelcontextprotocol.io](https://modelcontextprotocol.io/docs/getting-started/intro) |
| FastMCP | the framework Session 10 builds all six ways on: a tool, a server, `mount`, `CodeMode`, `from_openapi` | [gofastmcp.com — tools](https://gofastmcp.com/servers/tools) |
| UTCP | the manifest, if your capability already exists as an HTTP API | [utcp.io](https://www.utcp.io/) |
| `helpers/tools.py` | `Toolbox`: dispatch where a tool failure is a message, not an exception | [`helpers/tools.py`](../../helpers/tools.py) |

---

## Setting Expectations

**Budget six to eight hours**, spread across the week. The second
implementation takes an evening. The measurement takes an hour. The decision
row takes thirty minutes, and it answers *"what did you reject?"*

| Step | What it is | Rough time |
| :---: | --- | --- |
| 1 | Write down what the room asked | 20 min |
| 2 | Pick the second-best way, and say why | 30 min |
| 3 | Build it | 2–3 hrs |
| 4 | Measure both, at demo scale | 45 min |
| 5 | Measure again at your real response size | 30 min |
| 6 | Write the decision, with the switch condition | 30 min |
| 7 | Refine the demo and show it to a real stakeholder | 45 min, plus their calendar |
| 8 | Share: bring it to work | 20 min |

> **Do Step 1 today, while you still remember what was asked.** The questions
> fade fast, and the ones you could not answer are why this challenge exists.
> Book Step 7's audience at the same time.

---

## What you are building

| File | Role |
| --- | --- |
| Your existing `@app.api` endpoint | Implementation one, the baseline. Usually a tool |
| A second implementation of the same endpoint | Skill, subagent, MCP server, Code Mode, or UTCP manifest, whichever Step 2 picks |
| `measure.py` (or a cell) | The counter from Session 10, run over both: `Meter` plus a capability counter (`CapabilityCounter` middleware, or the deep dive's counting wrapper) |
| `use_case/decisions.md` | The room's questions, then the architecture row |
| `use_case/stakeholders.md` | Who saw the refined demo, and what they asked |
| `CLAUDE.md` | The instructions Claude Code reads before it touches anything |

> **What is already written for you, and what is not.** Session 10's five
> `call_with_*` functions and its `measure()` counter run unchanged against
> any capability that takes its function as an argument. Swap `who_is_oncall`
> for your retrieval call and the plumbing is done. The taught notebook's
> `dispatch` never raises, and neither does the `Toolbox` in
> `helpers/tools.py` that the deep dive uses. **The choice of second way, the
> implementation, the measurement at your real payload, and the decision row
> are yours.**

`CLAUDE.md` puts Claude Code into **instructor mode** for this directory. It
will explain, debug, and review. It will decline to write your second
implementation or your decision row. That is deliberate. The decision reads
like documentation, so having it drafted feels harmless, but it is the
assignment.

---

## Step 1 — Write down what the room asked

In Session 9, people who did not build your system asked you questions. Most
of them are what a real sponsor asks a few months in. Write them down now,
before they blur.

Under a `## Week 5 — what the room asked` heading in
[`use_case/decisions.md`](../../use_case/decisions.md), list every question
you were asked. Then mark three of them:

| Mark | Which | What you do with it |
| --- | --- | --- |
| **Fair** | Two questions that landed: a real gap, not a misunderstanding | Fix them. Step 7's demo shows the fix |
| **Open** | The one you could not answer | Answer it by Step 6, or say plainly in the decision row why it is still open |
| **Confusion** | Any that were really *"I did not follow your explanation"* | Rewrite that part of the demo, not the system |

*"What did you reject?"* is on the rubric's list. This challenge answers it.

> **If you did not write them down during the session**, use the rubric's
> *What the room asks* list and answer every question in it in writing. Mark
> the one you struggle with most as open.

### ✅ Deliverables

1. **The questions, in `use_case/decisions.md`**, with two marked fair, one
   marked open, and any confusion ones marked as such.
2. **One line per fair question** saying what you will change.

---

## Step 2 — Pick the second-best way, and say why

Session 10's ordering, in the order the questions resolve fastest:

| # | Question | If yes |
| :---: | --- | --- |
| 1 | Does the capability **already exist as an HTTP API** at work? | **UTCP**. Describe it, do not rebuild it. Settle who holds the credential |
| 2 | Does anything **outside your codebase** need to discover this? | **MCP**. Discovery is what the process boundary buys, and the only thing |
| 3 | Does one request need **several calls, or calls that return a lot**? | **Code Mode**. The intermediate data never enters the context |
| 4 | Does the **knowledge change more often than the code**? | **A skill**. Policy in markdown that a domain expert edits |
| 5 | Does the work **read a lot to produce a little**? | **A subagent**, to keep the parent's context clean |
| 6 | Otherwise | **A tool**. The boring answer, usually right |

Your endpoint is almost certainly a tool today. Walk the six questions for
*your* capability and find the first "yes" that is not "otherwise". That is
your second-best way. Write down the reason it is second best.

**Two constraints on the pick:**

- **It has to be buildable this week** against your real endpoint. If you
  have no sandbox that can run untrusted code, Code Mode is a paragraph in
  your write-up, not an implementation.
- **It has to be measurable** with the Session 10 counter. That rules out
  nothing, but an MCP server gets measured as a tool loop plus a process,
  because that is what it is.

### ✅ Deliverables

1. **The second way, named**, with the ordering question that selected it and
   one sentence on why the questions above it were "no".
2. **The closest alternative you did *not* pick**, and why. This becomes the
   *rejected* field in Step 6.

---

## Step 3 — Build it

Build a second implementation of the same endpoint. The capability underneath
stays the same (your retrieval call, your `solve()`). What changes is how the
model reaches it.

Session 10's code is the shape for each:

| Way | What you write | What Session 10 gives you |
| --- | --- | --- |
| **Skill** | A `SKILL.md` with the policy and a `run.py` that calls your capability | The directory layout, `SkillsDirectoryProvider` to serve it, and the plan-with-a-schema step that costs ~100 tokens instead of ~1,000 (measured in the deep dive) |
| **Subagent** | A second model call with its own prompt and only your capability's output in context | `call_with_subagent` (a tool whose body is a model call), and the warning that a subagent reciting from its prompt is stale |
| **MCP server** | `@server.tool` over your capability, on stdio; or Gradio's own MCP mode over the endpoint you already have | `oncall_fastmcp_server.py` (the deep dive's twelve-line `MCPServer` is the same idea), `mount` for putting it behind a platform server, and the `.mcp.json` to point Claude Code at it |
| **Code Mode** | A namespace exposing your capability and a prompt that asks for a program | `call_with_code_mode` on FastMCP's `CodeMode`, and the rule that `SAFE_BUILTINS` is not a sandbox. This one runs in a subprocess or container, or it does not ship |
| **UTCP** | A description of the HTTP API your capability already is | `FastMCP.from_openapi` over its OpenAPI document; the deep dive's hand-written manifest, `utcp_schemas` and `utcp_invoke` |

Whichever you build, the capability takes its function as an **argument**.
That lets Step 4's counter swap in a counting version without patching
anything.

> **Dispatch through something that does not raise.** Session 10 showed a loop
> with no name check running the wrong function with no error. Wherever the
> model's request meets your code, put `Toolbox` or its equivalent. A tool
> failure is a message to the model, not an exception in your process.

### ✅ Deliverables

1. **The second implementation, running**, answering the same requests as the
   first.
2. **Its dispatcher handling an unknown tool name and malformed arguments as
   messages**, with one line in your README showing what the model gets back.

---

## Step 4 — Measure both, at demo scale

This is Session 10's Task 5 (Task 7 in the deep dive), over your two
implementations instead of its five. Send the same two requests through each:
one that needs a single capability call, and one that needs several. Record
four numbers per run:

| Column | What it tells you |
| --- | --- |
| **model calls** | What the loop cost |
| **capability calls** | What the work *was*: how many times your function actually ran |
| **seconds** | Wall-clock, end to end |
| **tokens** | What crossed the model boundary, total |

**Don't skip the second column.** When model calls and capability calls
diverge, say four invocations behind one model call, you are seeing what
your architecture is actually doing.

If the second way is a skill or an MCP server, expect the counter to read
zero. The capability ran on the other side of a process boundary, where your
counter and your tracing cannot see. Write that blind spot down as a finding.

Before you read anything else in your output, check one thing: **how many
tool calls did your model make in a single turn?** If four lookups cost two
model calls, your model emits parallel tool calls, and the round-trip argument
does not apply to it. If they cost five, it does. Either way it depends on
your model and its server, and your decision row should say which.

### ✅ Deliverables

1. **The measurement table** in your README: two implementations × two
   requests × four columns.
2. **One line** on whether your model emitted parallel tool calls, with the
   count from `len(msg.tool_calls)` on the first turn.

---

## Step 5 — Measure again at your real response size

This is Session 10's payload sweep (Task 5's second half; Task 8 in the deep
dive), on your data. Demo-scale measurements flatter every architecture,
because real capabilities return more than a four-key dictionary. Make your
endpoint return what it really returns: the full retrieved passages with their
sources, the whole record, the actual document. Then run the same request
through both implementations again.

Record three things:

- the **size of one response in bytes**
- the **number of capability calls per request**
- the **tokens** for each implementation

Then put them next to the sweep's curve. Here is how each way's cost behaves:

- **Tool loop:** it reads every result back into the conversation, so its
  cost is roughly *calls × response size* on top of the conversation.
- **Code Mode:** flat, as long as the program returns only what the question
  needs. Making sure it does is the tool description's job.
- **Subagent:** whatever it read.
- **Skill and MCP:** the tool loop's cost plus a process.

> **This is the measurement that changes decisions.** At 118 bytes the two
> ways were within a few hundred tokens of each other. At 2.5 KB the tool
> loop cost 5× more in the taught notebook's run and 32× more in the deep
> dive's. Your endpoint returns more than 118 bytes.

### ✅ Deliverables

1. **The real-size row** in your README: bytes per response, calls per
   request, tokens for each implementation, marked *measured*.
2. **One sentence** on what that number does at 10× your current volume.

---

## Step 6 — Write the decision, with the switch condition

In [`use_case/decisions.md`](../../use_case/decisions.md), fill in the
architecture row that Week 1 left as `<!-- TC5 -->`:

| Field | What it means |
| --- | --- |
| **Decision** | Which of the six you are keeping |
| **What you rejected** | The other five in a line, and the closest one (the one you built) in detail |
| **Why** | In terms of the six ordering questions and the numbers from Steps 4 and 5: callers, knowledge churn, context, response size, existing API, who holds the credential. Not preference |
| **What would change your mind** | The trigger. A second client, a response size, a call count, a security review passing |

What a good row looks like:

> **Decision:** a plain tool.
> **Rejected:** MCP, most seriously, because we built it. It added ~90 ms and
> a process we would have to own. Our app is the only caller and will be for
> at least a year, so discoverability buys nothing. A skill is the wrong
> shape: the knowledge is in code, not policy. Code Mode was the interesting
> one. Our endpoint returns ~4 KB per call and two calls per request, so it
> would have cut tokens by roughly 5×. But we are not ready to run untrusted
> code, and that is a security decision, not an architecture one.
> **Switch condition:** the moment a second client needs this (the ops
> console is the likely one), MCP becomes worth the deployment. If
> per-request calls go above four, Code Mode becomes worth the sandbox.

It is concrete, it has numbers, it names the closest alternative, and it gives
a trigger. A rejection can be *for a reason outside architecture*. Saying so is
stronger than inventing a technical objection you do not hold.

What gets picked apart:

> **Decision:** MCP, because it is the standard.

No caller named, no alternative built, no number, no trigger.

*"My architecture is one prompt"* is fine. Say so and defend it. Plenty of
production systems are one prompt with good retrieval, and Week 1's challenge
asked whether this needed to be agentic at all. If the answer was no then and
is still no, write that down as your decision.

### ✅ Deliverables

1. **The architecture row**, all four fields, with the Step 4 and 5 numbers
   cited in *why*.
2. **The open question from Step 1, answered**, or the row says plainly why
   it is still open and what would close it.

---

## 🧯 If it's blocked

### "I only know how to do it one way"

That is why Session 10 exists. Build the second one from its code. The
capability there is trivial, so all you are learning is the plumbing. Start
from the `call_with_*` that matches your pick and replace `who_is_oncall` with
your function.

### "They all perform the same"

On latency, at your scale, they might. Say that: *"at 40 requests a day the
latency difference is unmeasurable, so I chose on maintenance cost"* is a
strong engineering answer. But check tokens before you conclude it, at your
real response size. Tokens are what separate them, and the gap widens as your
data grows.

### "My round-trip numbers don't match the session's"

They are not supposed to. Whether your model emits parallel tool calls
depends on the model and the server in front of it. Report what yours does.
That is your finding.

### "The counter reads zero capability calls"

Your second way is a skill or an MCP server, and the capability ran in
another process. The counter cannot see it, and neither can your tracing.
Count it on the far side (a log line in `run.py`, a counter in the server) and
write down that you had to. That is the cost of the process boundary.

### "`mcp` won't import"

You need `mcp` 2.0 or later (`uv add mcp`). The 2.0 release removed
`mcp.server.fastmcp`. `MCPServer` in `mcp.server` is the replacement, with the
same decorator API. A tutorial that imports `mcp.server.fastmcp` predates that
release, and its import no longer resolves.

Session 10's taught notebook uses the separate `fastmcp` package instead
(`from fastmcp import FastMCP`, version 4.1 or later, which itself needs `mcp`
2.x). Either works, but do not mix a tutorial for one with the import of the
other.

### "Code Mode hung"

The model probably wrote `while True:`, and nothing in an in-process `exec` limits
time. Restart the kernel. To get a timeout you need isolation: run the code in
a subprocess you can kill, or do not run it.

---

## 👥 Step 7 — Refine the demo, and show it to a real stakeholder

Don't give the same demo again. **Refined** means it answers what the room
asked. From Step 1:

- [ ] Fix the two fair questions, and show the fix.
- [ ] Answer the open one, or say plainly on the slide why it is still open
  and what would close it.
- [ ] Cut thirty seconds of stack description and spend it on the problem.
- [ ] Show a failure on purpose, if you did not already.
- [ ] Add one line to the numbers section: the architecture decision, the
  Step 5 number that backs it, and the way you rejected, by name. Session
  10's platform engineer gave her board six answers for six teams. You owe
  the room one answer with one reject.

Then **show it to someone real**: the person from your charter, the person who
would fund the seat, or whoever is closest. Five minutes, timed, then their
questions. A screen-share counts. A recording you send and they reply to
counts. Imagining how it would go does not.

**Ask three things, in this order:**

1. *"What would you do differently on Monday if this is right?"*
2. *"What did I say that you did not believe?"*
3. *"What is the worst thing this could do, from where you sit?"* The answer
   is a candidate for the guardrail you build next.

> A demo that has visibly absorbed criticism is more credible than one that
> was polished from the start. Say out loud what changed and why.

> **Your agent will help you tighten this, and will not invent it.** Ask it to
> time the sections, to cut the stack slide, or to turn messy notes into three
> findings. It will decline to write the feedback itself, because it was not
> in the room.

### ✅ Deliverables

1. **A row in [`use_case/stakeholders.md`](../../use_case/stakeholders.md)**:
   who you showed it to by role, what you asked, what you learned, and the
   follow-up.
2. **A line in [`use_case/decisions.md`](../../use_case/decisions.md)** naming
   one thing their questions changed: a number added, a claim cut, a switch
   condition sharpened. If nothing changed, write that and say why.
3. **What changed after critique**, in one paragraph at the top of your
   README, so a reader can see the demo absorbed it.

---

## 📤 Step 8 — Share: bring it to work

This week's pattern: *build the alternative before you reject it, and measure
at the size your data really is*. Look for one of these at your company:

- a capability is being wrapped in an MCP server for one caller
- a tool loop reads 20 KB responses into a context window on every request
- an HTTP API that has run for four years is about to be rebuilt as a service
  that forwards calls to it

This step is where you write down which one.

### ✅ Deliverables

1. **Which capability at work this is for**, one line under `## Bring it to
   work` in your README. *"The ticket-lookup API the support bot wraps in
   an MCP server that only the support bot calls"* names one. *"Our agent
   platform"* does not.
2. **What you would swap**: three lines under the same heading, one each for
   - the **data**: what the capability really returns, in bytes, and how many
     calls a request needs
   - the **model or endpoint**: whether the capability already exists as an
     HTTP API, and who would hold the credential
   - the **access or approval** you would need to ask for: a sandbox for
     untrusted code, a deployment target for a server, a token for a client

   Put the Step 5 token number next to them, marked *measured*. These lines
   turn the comparison into the version your team could run.
3. **Your repo link posted in [our community on Maven](https://bit.ly/fde1-maven-community)**,
   and comments on at least two other students' submissions after the deadline.

---

## What this challenge deposits for later

| What you write | Where it lives | When it comes back |
| --- | --- | --- |
| The architecture row, with the switch condition | `use_case/decisions.md` | **Week 9**, when the deployment checklist asks what runs where and who holds which credential. **Week 10**, where the handoff doc is largely this file. |
| The second implementation | Your app | **Week 6.** A tool description is text a model reads and acts on, so the one you wrote this week is an injection surface. Code Mode's namespace is the one you escape. |
| The measurement at real response size | Your README | **Week 7.** Memory is retrieval over a corpus that grows, and this number says what growing costs. **Week 9.** The concurrency and latency numbers the deployment checklist wants. |
| The room's questions, and who saw the refined demo | `use_case/decisions.md`, `use_case/stakeholders.md` | **Week 10.** The final report answers the same questions, to a bigger room. |
| The three swap lines | Your README, `## Bring it to work` | **Week 10.** The final report's "what it would take to run" section. |

---

## Your Final Submission

Please include the following in your final submission:

1. **A public link to your repo**, containing:
   1. **A five-minute-or-less Loom video** of the refined demo. Open with
      what changed after critique, and lead with the problem, not the stack.
   2. **A written document addressing each deliverable above**:
      - the room's questions with their marks
      - the second way and why
      - the dispatcher's failure messages
      - the demo-scale measurement table, with the parallel-tool-call count
      - the real-size row
      - the architecture row
      - the Step 7 answers
      - the swap lines
   3. **All relevant code**, committed and pushed: both implementations and
      the measurement. **Never the data.**
2. **Your `use_case/` directory updated**: the Week 5 questions and the
   architecture row in `decisions.md`, and the new row in `stakeholders.md`.

### How to submit

1. **Post your repo link** in
   [our community on Maven](https://bit.ly/fde1-maven-community). That is where
   every technical challenge is submitted.
2. **Push your `use_case/` updates to that repo** before you post, so the link
   shows the current state of your project.
3. **After the deadline, comment on at least two other students' submissions.**
   Read their architecture row and leave something specific: a switch
   condition you would push on, a reject they did not measure, or the one
   question from the rubric they still have not answered.

> **Never commit real company data.** `use_case/data/` is gitignored for this
> reason. If your second implementation talks to a real internal API, commit
> the manifest shape with the hostname removed, and never the credential. Do
> not post screenshots of internal infrastructure, hostnames, or anything your
> firm would consider confidential.

---

<!-- deliverables:start -->
## 🏗️ Build | 🚢 Ship | 📤 Share

Three escalating bars. **Build** means it runs for you. **Ship** means someone
else can run it. **Share** means someone who is not you has an opinion about it.

### 🏗️ Build

A second implementation of your endpoint, in the way you judged second best,
measured against the first at your real response size. That measurement is
what lets you defend the decision.

Four questions are asked inside the Session 10 notebook as you work through
it. *They are not submitted and not graded.* They help you work out what the
challenge is going to ask you for.

| # | Question | Asked in |
| :---: | --- | --- |
| 1 | What your endpoint's dispatcher does today on a tool name it does not have, and which of the five failure rows a user of your app would meet first | S10 |
| 2 | Who outside your codebase would need to discover your capability in the next year (a named client), and what MCP buys you if the answer is nobody | S10 |
| 3 | How many bytes your endpoint really returns per call, how many calls a request needs, and where that puts you on the tool-loop slope | S10 |
| 4 | Which of the six ordering questions decides it for *your* endpoint, and the condition under which you would switch | S10 |

> **Jumping to one.** Open the notebook, then add the anchor to your browser's
> address bar, for example `#discuss-question-3`. It works once the notebook has finished loading.

### 🚢 Ship

This is the graded part. Every item comes from a numbered step in the technical
challenge, which has the full detail.

- [ ] **The room's questions written down** in `use_case/decisions.md`: the two you will fix, and the one you could not answer
- [ ] **A second implementation of your endpoint**, in the way you judged second best, running
- [ ] **Both implementations measured**: model calls, **capability calls**, latency and tokens, on the same two requests
- [ ] **The token measurement repeated at your endpoint's real response size**, with the size in bytes recorded
- [ ] `use_case/decisions.md` has the architecture row: decision, closest reject, why in terms of the six questions, and **switch condition**
- [ ] It still runs in Docker

### 📤 Share

- [ ] **The refined demo, shown to a real stakeholder**, with what changed after critique and what they asked, recorded in your own words. Graded
- [ ] **What you would swap to run this at work**: data, model or endpoint, and the approval you would need, as three lines in your README
- [ ] Your repo link posted in [our community on Maven](https://bit.ly/fde1-maven-community)
- [ ] Comments on at least two other students' submissions, after the deadline
<!-- deliverables:end -->

---

## Where this goes next

| Week | What it adds to this decision |
| --- | --- |
| 6 | Guardrails. The tool description you wrote is an injection surface, and you escape the Code Mode namespace on purpose. |
| 7 | Memory. Retrieval over a corpus that grows, measured with the same counter, so you know what growing costs. |
| 8 | Fine-tuning. The model behind the loop changes, so re-measure whether it still emits parallel tool calls first. |
| 9 | Infrastructure. Which process runs where, and who holds which credential, is the deployment checklist's first page. |
| 10 | Production. The refined demo becomes the final readout, and the decision row becomes the handoff doc. |

Everything after this week assumes you chose your architecture with a
measurement and can say what would change it.

---

## Step 2 — the second way, and the closest reject

**Capability:** `find_existing_loads(refs)`: the loads already in the TMS that match an email's PO, pickup and load refs.

**Implementation 1 (baseline): a pipeline.** Code looks up the refs before the draft, and any match goes into the prompt. It looks them up again after the draft, and a match always sends the order to a person as an update. One model call.

**Implementation 2 (the second way): UTCP.** A manifest describes the TMS's existing lookup web service (find a shipment by reference, then extract it), and the model calls it as a tool. The same after-check runs on both, so the comparison measures one thing: whether the model is given the lookup or fetches it itself.

**Why UTCP:** ordering question 1. The capability already exists as an HTTP API: the lookup works in the broker's TMS sandbox and is used there every day. Describe it, don't rebuild it. It's the first question, so none above it were "no".

- *What it can prove:* the description is right (find a shipment by PO and read its fields back); the update path works end to end; how big one lookup reply really is (Step 5); and switching to production becomes a config change, not new code.
- *What it can't prove:* routing on real traffic, because the sandbox holds only test orders and none that ops entered. And it can't prove anything about the TMS's REST API, because nobody knows how its tokens are issued, so this uses the XML lookups proven in the sandbox.
- *Admitted:* the API is XML over one POST endpoint with no OpenAPI document. So the manifest is hand-written, and a small adapter builds the XML envelope. That part is partly rebuilding, not purely describing.

**Closest reject: Code Mode.** A 5-PO email means 5 full shipment records, and Code Mode would keep them out of the model's context. But intake's lookups already run in code, not in a model loop, and there's no sandbox here for untrusted code. Switch only if intake becomes an agent that chooses its own lookups and a request needs more than one record read: each read is about 4,500 tokens, re-sent every later round (measured in Step 5; see the Step 6 row).

**MCP:** there's no outside client. Staff's future assistant would be my own app built on the history page, which can call the lookup directly.

## Step 3 — build

### Setup: a TMS sandbox the goldens can look up

The capability under test looks up loads already in the broker's TMS, so the goldens need real loads to find. `use_case/evals/tms_fixture.json` holds one redacted load for each golden that refers to a load already entered (15, 17, 20, 21). `use_case/evals/seed_sandbox.py` creates them in the TMS sandbox.

- **Fenced off from production.** Every ref starts `ZZFDE` and every Intake ID starts `CL-FDE-`, and the seeding script refuses anything else, or any enterprise that isn't a sandbox. The broker's production pipeline already ignores sandbox-owned loads in both its routing and its daily sandbox-vs-production check, and now also skips both markers.
- **Each load is set up to test one thing.** Golden 15's load carries the *old* PO, so only the SO finds it. Golden 21's carries the PO plainly, while the email writes it as `P003` + PO.
- **Known limit:** the sandbox is the TMS *as of now*, not as of each email. Goldens 2 and 20 are the same order (before and after it was entered), so golden 2 keeps a different ref. Otherwise its lookup would find the load entered later. As-of-aware lookups are a production need, left for later weeks.

### What the real API taught me

1. **Callers are allowed by IPv4 address.** My laptop called over IPv6 and was refused. Forced to IPv4, its home address wasn't on the list either. Development calls now go through an SSH tunnel from the broker's server, whose address is allowed. In production these calls run from that server anyway. *Effect on measurement:* the UTCP side's latency includes the tunnel hop; tokens don't.
2. **Lookup is an exact string match.** A dock system writes PO `24645400` as `P00324645400` (P + facility 003 + PO), so the exact lookup misses it. The fix is a rule table (data, not code) that also tries the PO inside a known pattern: one extra lookup, and no guessing at short tails that could match another load.
3. **"No match" and "the lookup failed" must never look the same.** An empty reply means no load matches. A failure raises an error. If a failure read as "no match," the order would be treated as new, which is the duplicate this work exists to prevent.
4. **One full shipment record is 10,216 bytes** (measured), roughly 3,000 tokens. That's 4× the top of Session 10's payload sweep, before Step 5 even starts.
5. **"Success" doesn't mean success.** The import service answers SUCCESS even when the import failed; the failure is inside the reply's logs. The client checks there.
6. **Writes are harder than reads.** Every import needs a payment block, but an update can't change the bill-to the TMS set at creation, so it rejects the whole update. Anything that writes to this TMS has to remember each load's bill-to. The seeding script is therefore create-only. This doesn't affect this week's lookups, but it matters for the eventual "agent enters the order" goal.
7. **A shared TMS means other loads can match.** Golden 3's PO matched another team's test load in the same sandbox, and the pipeline correctly escalated a quote as an update. The eval now passes in a `lookup` that only sees the course's own loads, so the sandbox behaves like the TMS as of these emails. In production the same collision needs an "as of this email" check.
8. **"TMS failure" has to include "TMS unreachable."** A dead tunnel raised Python's own network error, not the client's `TMSError`, so it would have crashed intake instead of sending the order to a person. The client now turns every network failure into a `TMSError`.
9. **The shared after-check has to be told exactly what was looked up.** On the UTCP side, assuming the ref rules had been applied to the model's own lookups would have skipped `ZZFDE21PO1`. That would have let a duplicate through if the model had called the order new.

### The adapter (admitted, as promised in Step 2)

`01_Product_Engineering/challenge/tms_client.py` is the small piece that builds the TMS's XML. One function, `call()`, touches the network. `lookup`, `extract` and `import_order` only build the XML they send. `summarize()` trims a 10 KB record down to the ~300 bytes the checks use (shipment ID, refs, status, dates, zips, temperature, pallets, weight). Every request and reply is saved locally, which is where Step 5's byte counts come from.

### Built

- **The capability:** `find_existing_loads(refs, lookup, extract)` in `existing_loads.py`. `lookup` and `extract` are passed in, so the real TMS client, the eval's fixture filter and Step 4's counter all plug in the same way. It doesn't catch TMS errors, because an empty list means "no match" and a failed lookup must never look like that.
- **Implementation 1, the pipeline** (`solve_with_lookup`): a before-check on the email's labeled refs, one model call with any matches as a 166-token block, and an after-check on the draft's other refs. Any match forces a person; any TMS failure also goes to a person.
- **Implementation 2, UTCP** (`utcp_tms.py` + `tms_utcp_manifest.json`): the manifest describes the TMS's two real operations, and the model calls them as tools. It runs the same after-check, and a TMS failure during the loop also goes to a person, whatever the model concluded.
- **The dispatcher** is the course's `Toolbox`, set to pass full records (its 4,000-character default would have hidden 60% of one). What the model gets back on a mistake:
  - unknown tool: `{"error": "unknown tool 'lookup_load'; available: find_shipment_by_reference, get_shipment"}`
  - malformed arguments: `{"error": "arguments were not valid JSON: '{bad json'. Send a JSON object."}`

## Step 4 — both implementations measured, at demo scale

The same three goldens through both implementations, one run each, measured by `use_case/evals/measure_ways.py`. Model calls and tokens come from a LiteLLM callback, the same counter for both sides. Capability calls come from a counting wrapper around `lookup` and `extract`, passed in like everything else (nothing patched). Seconds are end to end, including the TMS calls through the development tunnel.

| Golden | Request | Way | Model calls | Capability calls | Seconds | Tokens |
|---|---|---|---|---|---|---|
| 2 | one ref, no load | pipeline | 1 | 1 (1 lookup) | 6.1 | 7,116 |
| 2 | | UTCP | 2 | 1 (1 lookup) | 7.2 | 15,162 |
| 15 | three refs, one load | pipeline | 1 | 4 (3 lookups + 1 extract) | 15.3 | 9,731 |
| 15 | | UTCP | 3 | 4 (3 lookups + 1 extract) | 12.9 | 32,662 |
| 17 | one ref, one load | pipeline | 1 | 2 (1 lookup + 1 extract) | 12.2 | 8,618 |
| 17 | | UTCP | 3 | 2 (1 lookup + 1 extract) | 12.1 | 29,626 |

- **Capability calls are identical on both sides.** The TMS did the same work whichever way the model reached it.
- **Model calls and tokens are what differ:** the tool loop costs 2.1–3.4× the tokens for the same work. Even with nothing to find (golden 2) it pays a second model call, because each round re-sends the whole prompt.
- **Latency is even** at this scale (6–15 s on both sides). It's dominated by how much the model writes and by the TMS calls. Tokens separate the two, not seconds.
- **Parallel tool calls:** Opus 5.5 emits them. Golden 15's first UTCP turn had `len(msg.tool_calls)` = 3 (all three lookups at once), so 4 capability calls cost 3 model calls, not 5. The tool loop's extra cost is re-sending the conversation each round, not one round trip per lookup.

**The same comparison on all 21 goldens** (`run.py --pipeline` / `--utcp --compare`): both miss 1 of 9 escalations (golden 14, a load-board tender that no ref check can catch), down from 4 for the draft alone, and both wrongly escalate 1 of 12 (golden 19). The pipeline used 21 model calls and about 164K tokens; UTCP used 46 model calls and about 390K tokens (**2.4×**) for the same accuracy.

## Step 5 — measured again at real response size

The UTCP side reads what the TMS really returns: the whole shipment record. The pipeline trims it in code to a ~300-byte summary.

| Real-size row (all *measured*) | |
|---|---|
| Bytes per response (one full record) | 8,629–8,689 (course loads); 10,216 (another test load in the same sandbox) |
| Into the model's context per record read (UTCP) | ~4,500 tokens (golden 15: input 9,066 → 13,640 between rounds 2 and 3) |
| Into the prompt per matched load (pipeline) | 166 tokens (the summary line; identical on all four matched goldens) |
| Capability calls per request | 1–8 (1–4 lookups + 0–4 extracts) |
| Tokens per order, pipeline | 7,116–9,731 (about 7,800 on average across 21 goldens) |
| Tokens per order, UTCP | 15,162–32,662 (about 18,600 on average across 21 goldens) |

**A 4-ref request**, a synthetic email naming four real sandbox loads (`use_case/evals/synthetic_4_refs.txt`):

| Way | Model calls | Capability calls | Record bytes fetched | Seconds | Tokens | 1st-turn tool calls |
|---|---|---|---|---|---|---|
| pipeline | 1 | 8 (4 lookups + 4 extracts) | 34,286 | 10.9 | 7,433 | — |
| UTCP | 2 | 4 (4 lookups) | 0 | 9.5 | 15,396 | 4 |

**It overturned my Step 2 prediction.** I expected "5 POs means 5 full records in context." For a status question, the model looked up all four refs in one turn, saw they all existed, and escalated without reading any record. On goldens 15, 17 and 20 it did read the record, to work out what the email changed. **So the tool loop's cost depends on what the model decides to read, and that can't be promised in advance.** The pipeline did more TMS work here (8 calls, 34 KB fetched), but only about 660 tokens reached the model. It's cheaper in tokens, not automatically in TMS calls.

*Estimated, not measured:* if the model reads every record on a 4-ref email, that adds roughly 18,000 tokens to every round after the records are read.

**At 10× today's volume** (about 800 emails a day, roughly 350 about a load already in the TMS), tokens rise from about 0.6M to 6.2M a day on the pipeline and from about 1.5M to 14.9M on UTCP, and TMS calls to as many as 6,400 a day (measured averages × volume). This treats each email as one order, since the token averages are per order, and the goldens aren't the real mix of mail.

**Still runs in Docker.** Both implementations are endpoints in the image (`/draft_shipment_checked`, `/draft_shipment_utcp`). Inside the image they use a stand-in TMS built from `tms_fixture.json`: no TMS login, no tunnel, no route to the real TMS. Only the model settings are passed in, from a separate env file. Two things the image caught that local runs didn't: code that assumed the repo's folder layout (fixed), and files only their owner could read, refused because the app runs as a non-root user.

## Step 6 — the decision

The architecture row is in [`use_case/decisions.md`](../../use_case/decisions.md) (Week 5): **the pipeline for intake**, with UTCP rejected after building and measuring it (same accuracy, 2.2× the model calls, 2.4× the tokens). Switch conditions: MCP when an assistant I didn't build needs the lookup; UTCP or a plain tool if more than 15% of "existing order" emails can't be matched by code after the index is widened (24% today, before widening); Code Mode only if intake becomes an agent and a request needs more than one record read. The Step 1 open question (partial loads) is answered there as still open, with what would close it.

## Bring it to work

**The capability:** order intake at the freight broker. The agent reads order emails from customers and the broker's own staff, creates and updates orders in a sandbox copy of the TMS, and checks the TMS for a load already entered under the email's PO, SO or load number before treating anything as new. A daily email compares its orders with what ops entered in production.

- **Data:** one TMS shipment record is 8.6–10.2 KB, about 4,500 tokens if a model reads it. An email carries 1–4 refs, so 1–8 TMS calls. About 80 business emails a day reach the agent (not all are orders), and about 44% of them are about a load already in the TMS.
- **Model or endpoint:** the capability already exists: the TMS's own web service. Today it's called on the production instance, against a sandbox enterprise. The broker's co-owners own the vendor relationship. Production needs a dedicated web-service user, held only on the broker's server: the TMS only accepts calls from listed IP addresses. The vendor can't limit a user to read-only services, so read-only is enforced on my side (the code only calls the lookup and extract services), and the password stays in that one place.
- **Access or approval:** approved in the 11/10 review: a new intake address, set up with the broker's IT contact; in production, customers' and staff's order emails are copied to it. Sending customer email to the AI provider: a verbal OK from the co-owner, with written sign-off still to get. Still to ask: the production TMS user, IP-restricted to the server.

**Measured** (Step 5): about 7,800 tokens per order with the lookup done in code, against about 18,600 when the model calls the TMS itself.

## Submission (TC5)

- **Loom (five minutes or less):** [TC5 demo](https://www.loom.com/share/e32d28641d014b59b45f4e1ac75546b1)
- **Branch:** `tc5`. Production data stays local (gitignored); goldens and the TMS fixture are redacted.

| Deliverable | Where | In one line |
| --- | --- | --- |
| The room's questions, marked (Step 1) | [decisions.md](../../use_case/decisions.md), "Week 5 — what the room asked" | Two fair (report and gate misses; check the TMS in code), one open (partial loads) |
| The second way, and why (Step 2) | [Step 2](#step-2--the-second-way-and-the-closest-reject) | UTCP, picked by ordering question 1; closest idea not built: Code Mode; MCP: no outside client |
| Both implementations, running; dispatcher failure messages (Step 3) | [Step 3](#step-3--build) | The pipeline (`existing_loads.py`) and UTCP (`utcp_tms.py` + manifest); unknown tools and bad arguments come back as messages |
| Demo-scale measurement, parallel tool calls (Step 4) | [Step 4](#step-4--both-implementations-measured-at-demo-scale) | Capability calls identical; UTCP 2.1–3.4× the tokens; 3 tool calls in one turn |
| Real-size row, 10× volume (Step 5) | [Step 5](#step-5--measured-again-at-real-response-size) | One TMS record 8.6–10.2 KB (~4,500 tokens); pipeline ~7,800 vs UTCP ~18,600 tokens per order |
| Architecture row, switch conditions (Step 6) | [decisions.md](../../use_case/decisions.md) (Week 5) · [Step 6](#step-6--the-decision) | The pipeline; UTCP rejected after building it; switch at 15% unmatched updates, more than 1 record read, or an outside client |
| Still runs in Docker | [Step 5](#step-5--measured-again-at-real-response-size) (last paragraph) · [Dockerfile](../../01_Product_Engineering/challenge/Dockerfile) | Both endpoints in the image, against a stand-in TMS; no TMS login inside |
| Refined demo shown to a stakeholder (Step 7) | [stakeholders.md](../../use_case/stakeholders.md) (Week 5) · the paragraph at the top | The co-owner: "the first thing to look at"; worst case "a wild goose chase"; new guardrail: duplicate appointments |
| What I'd swap to run it at work (Step 8) | [Bring it to work](#bring-it-to-work) | Production TMS user on the broker's server; written AI-provider sign-off; the new intake address |
