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

**Access control depends on email admin access.** Per-user permissions on the
retrieval tools (see the Week 3 decision) can only come from the source if we
index each person's mailbox through Microsoft 365 directly. Until the admin
account is recovered, the corpus is a static export, and permissions have to be
rebuilt as tags at index time.

---

## Week 9 — the full checklist

<!--
  TC9 extends this same file. Do not start a new one: the point is that the git
  history shows one continuous piece of work from Week 1 to Week 9.
-->

<!-- Week 9 -->
