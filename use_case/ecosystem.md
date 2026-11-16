# The ecosystem you deploy into

Where your application would actually run, inside your actual firm.

> **Week 1 starts this file. Week 9 finishes it.**
> TC1 Step 10 asks eight questions. The full Week 9 checklist has around thirty,
> and the eight are a strict subset — so nothing here gets thrown away.

Describe patterns, not specifics. "On-prem OpenShift, images from an internal
registry, no public egress" is useful to everyone and identifies nobody. Never
put real hostnames, IPs, or architecture diagrams in this file.

---

## Week 1 — the first eight questions

<!-- Answered in TC1 Step 10. Bring these back from a real conversation. -->

**Who did you ask?** (role, not name)

Co-owner of the freight brokerage. Internal tooling is run by an outside consultant (me), so I'm also the partial platform owner.

| # | Question | Answer |
| :---: | --- | --- |
| 1 | Where do internal apps run? (k8s, ECS, App Service, a VM someone maintains) | A small Ubuntu cloud VM I administer, which already runs a production report. This app would run there in Docker behind Nginx on its own subdomain. |
| 2 | Which cloud? AWS, Azure, GCP, on-prem, several? | AWS (Lightsail), under my consulting company’s account; DNS through Cloudflare. |
| 3 | Is there an internal container registry? | None. Build the image on the server, or push to a private GitHub or AWS registry. |
| 4 | How do users log in? (Okta, Entra ID, Ping, SAML, homegrown) | Email runs on Microsoft 365, but need to figure out admin access. Per-person passwords at Nginx for the trial. |
| 5 | Can the app reach the internet? Egress proxy? Allowlist? | Open outbound; the server already calls the TMS web services and an external LLM. The TMS’s production web services only accept this server’s address. |
| 6 | Where do secrets come from? (Vault, Secrets Manager, Key Vault) | A .env file on the server; no secrets manager. |
| 7 | Who approves a deployment, and what review does it need? | The owners; no formal review. The TMS vendor separately approves production web-service access. |
| 8 | Is there an approved internal LLM endpoint already? | None. A direct Anthropic API key paid by my consulting company; alternatives if needed are AWS Bedrock, Microsoft’s AI service, or a self-hosted model. |

**What surprised you?**

Nobody internally knows how to access the Microsoft 365 admin, so single sign-on is blocked.

**What would you have to change about your app to deploy there?**

- Run behind Nginx on localhost only, with TLS and per-person passwords for the trial; switch to MS 365 once admin account is recovered.
- Put `@gradio/client` in the image instead of loading it from CDN.
- Read the api key from a .env on the server, not from the repo.
- Add a restart policy and send logs so that they can be seen.
- Check memory, and likely size up the instance.
- Don't let it run the mailbox-reading job.

---

## Week 1 — what your machine told you
**10/08/2026**

host	why	status	signed by
pypi.org	Python packages	OK	GlobalSign nv-sa
files.pythonhosted.org	the actual wheel downloads	OK	GlobalSign nv-sa
api.openai.com	the model API	OK	Google Trust Services
cdn.jsdelivr.net	the CDN the Week 1 frontend uses	OK	Sectigo Limited
huggingface.co	open weights, Weeks 2 and 8	OK	Amazon
registry-1.docker.io	container images	OK	Amazon
github.com	this repository	OK	Sectigo Limited
Verdict: Open network, public CAs, no proxy. Nothing here will bite you.

**Does this match what you were told in the table above?** Where it doesn't, that
gap is worth chasing — it usually means a proxy nobody documented.

---

## Week 3 — retrieval dependencies

**Was the CLIP download blocked?** No. The network is open (see Week 1), and the
CLIP and local text-embedding models downloaded from Hugging Face on the first
run, without a token (unauthenticated, so rate-limited, but it completed).

**What I'd do in production anyway:** bake the model files into the Docker image
at build time and pin the version, rather than downloading on first use. There is
no internal artifact store, so the image (pushed to a private registry) is the
artifact store; the model becomes a versioned dependency like any other, and a
Hugging Face outage or rate limit can't break a restart.

**Probably not needed at all:** my non-text content is scanned documents (bills of
lading, POs, appointment confirmations), and the plan is to parse them to text
(Strategy A), not search them by pixels. If that holds after measuring, CLIP never
ships.

**Which vendors would see customer data:**
- Vision parsing of scans: the same LLM provider already used for chat, under
  the same key and the owners' existing OK. No new vendor.
- Hosted text embeddings: a second provider would receive the text of customer
  orders and emails. The owners are fine with an additional AI vendor (confirmed
  10/23/2026), so this is approved. Fallback if that ever changes: a local
  embedding model in the image (no data leaves the server), or BM25 alone,
  which needs no model.
- A hosted multimodal embedding endpoint: not considered. It would add a third
  vendor for content that isn't actually visual.

**Mail access now comes from Microsoft 365, scoped to one mailbox (updated 10/26).** A registered app
reads one co-owner's mailbox read-only through the Microsoft Graph API (Mail.Read, limited by the tenant
to that mailbox; a test against a second mailbox was refused). A job on the broker's server runs every 15
minutes on weekdays, keeps only business mail (newsletters, billing and system mail are skipped and
never downloaded), and the app reads what has been pulled since the export.
- What it changes: the corpus is no longer only a static export, and per-mailbox access is now
  possible at the source rather than rebuilt by hand.
- What it doesn't: the one mailbox still receives copies of the shared order, dispatch and accounting
  addresses and of the other co-owner's mail, so per-user permissions on the retrieval tools still have
  to be rebuilt as tags at index time (see the Week 3 decision). Indexing each person's own mailbox is
  the cleaner route, and it now needs only that mailbox added to the app's scope.
- Still missing: TMS shipments don't update from this feed (it skips the broker's own carrier tenders,
  where the rate confirmations come from); that needs the TMS export, held for Week 5.

---

## Week 6 — who can write to what it reads

- Email body and subject line: today, anyone who can get mail into the one co-owner's mailbox the app reads through Microsoft Graph (see Week 3). That includes anyone who emails that co-owner directly, anyone who emails the shared order, dispatch or accounting addresses, and anyone who emails the other co-owner, because copies of all of those land in that mailbox. Go-live plan: a separate intake@ address that only the app reads, so the writer becomes anyone who can email intake@, which means anyone on the internet who has the address.
- Quoted thread history: everyone who has ever written in the thread, including colleagues’ earlier replies and forwarded third parties
- Attachments (PDFs, scanned BOLs, packing lists): often a third party (the shipper), forwarded by the customer
- Images the model reads (appointment screenshots): the receiving facility’s system
- From address and sender name: anyone, since it’s easy to fake, and it decides which customer profile is loaded
- Customer profiles (graded app): generated from TMS shipment records (`wiki.py`), not from email. Writer: whoever can write those records, meaning ops and anyone else the TMS lets edit a load (the same writers as the TMS line below). Building profiles from past emails is ColdLade's production plan. If that ships, the writer becomes anyone who ever emailed.
- Stored history corpus (`answer_from_history` in `01_Product_Engineering/challenge/app.py`: past emails, shipments and attachments): anyone who ever emailed, plus the third parties behind forwarded attachments and the TMS editors behind shipment records. This is a separate source from the live inbound email. A poisoned email from months ago can resurface in a different person's query long after anyone has stopped looking at it.
- TMS records returned by lookups: ops, and anyone else the TMS lets edit a load
- Question box (the free-text question passed to `chat()` and `answer_from_history(question=...)`): colleagues signed in with the per-person Nginx passwords (trial), later Microsoft 365 sign-in. Trusted, but it is still an entry point, and anything pasted into it (an email snippet, a customer's text) brings that text's writer along with it.

I’d poison an attachment first. It’s often written by a third party, not the customer, so an honest customer forwards it without reading every line, and instructions can be hidden where a person won’t see them but the model will (white text on a white background in a PDF). It has already happened by accident: a shipper’s own “Bill To” field steered the model into the wrong value.

---

## Week 9 — the full checklist

<!--
  TC9 extends this same file. Do not start a new one: the point is that the git
  history shows one continuous piece of work from Week 1 to Week 9.
-->

<!-- Week 9 -->
