# Empório da Música — AI customer-service agent

A prototype text-message assistant for **Empório da Música**, a fictional musical-instrument
store in Campo Grande/MS, Brazil. It chats with customers in Brazilian Portuguese. It looks up
products, prices, stock, promotions and orders in the store's data, and it answers
store-policy questions (opening hours, payment, returns, shipping, warranty) from the store's
policy manual. Built in Python for the Artefact AI Engineer technical case.

> **Status: in development.** Sections marked _(planned)_ describe approved designs that are not
> implemented yet. The README is updated at every stage. See the
> [progress table](#progress) and the [changelog](CHANGELOG.md).

## Contents
1. [Overview](#1-overview)
2. [Quick start](#2-quick-start)
3. [How it works](#3-how-it-works)
4. [Technical decisions](#4-technical-decisions)
5. [Security & cost safeguards](#5-security--cost-safeguards)
6. [Deploying your own proxy](#6-deploying-your-own-proxy)
7. [Assumptions](#7-assumptions)
8. [Known limitations & future work](#8-known-limitations--future-work)
9. [Testing & evaluation](#9-testing--evaluation)
10. [Example conversations](#10-example-conversations)
11. [How AI coding assistants were used](#11-how-ai-coding-assistants-were-used)
12. [Repository layout](#12-repository-layout)

## Progress
| Stage | Status |
|---|---|
| Project guidelines (`CLAUDE.md`), case data, scaffold | Done |
| Documentation skeleton and decision log | Done |
| Data layer and unit tests | Done |
| Policy manual transcription and fidelity test | Done |
| Tools, prompt, agent loop, command-line chat (direct mode) | Planned |
| Hosted proxy (FastAPI on Render) and proxy mode | Planned |
| Scenario evaluations (Haiku 5.5 vs Sonnet 5.5) | Planned |
| Example conversations | Planned |
| Final documentation and submission PDF | Planned |

## 1. Overview
What the agent does:
- **Persona:** the store's virtual assistant, in the tone the manual asks for: informal but
  professional, like a friend who knows music.
- **Live data:** it decides when to query products, stock, prices, promotions or order status,
  and never quotes a number without checking it.
- **Policies:** it answers from the store's manual: opening hours, payment and installments,
  returns, shipping, warranty and privacy.
- **Scope:** it politely declines anything outside the store's scope (accessories, off-topic
  requests) and hands complaints and unclear cases to a human.

## 2. Quick start
_(planned: completed in the proxy and agent stages)_

Two ways to run it. Both use the same agent code:
- **A. Hosted proxy (default, no API key needed):** you run the agent locally, and its model
  calls go through the author's proxy. You need the access code sent with the submission. It
  is not published here, to protect the API budget.
- **B. Your own Anthropic API key (direct mode):** put `ANTHROPIC_API_KEY` in `.env`, and the
  agent calls Anthropic directly.

Setup available today:
```
git clone https://github.com/rael-peixoto/emporio-da-musica-agent.git
cd emporio-da-musica-agent
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # Windows
# .venv/bin/python -m pip install -r requirements.txt       # macOS / Linux
.venv\Scripts\python -m emporio --help
```

## 3. How it works
_(planned design; see [`docs/implementation-plan.md`](docs/implementation-plan.md))_
```
                ┌─ direct:  Anthropic SDK ──────────────────────────► api.anthropic.com
CLI ─► agent ──┤            (your own key)
 (local tools, └─ proxy:   Anthropic SDK, base_url=Render URL ─► FastAPI proxy ─► api.anthropic.com
  local data)              api_key = access code                (key kept server-side)
```
- **Agent loop:** Claude decides whether to answer directly or call a tool. Tools run locally
  in Python over the CSV files and return exact, pre-computed values.
- **Tools:** product search, product details (price, active promotion, PIX price, maximum
  interest-free installments), category list, verified order lookup, and human handoff.
- **Prompt:** in pt-BR. It holds the persona, the ground rules, the interpretation notes and
  the full policy manual, and is cached. The current date/time and whether the store is open
  are added in a separate block after the cached part.

## 4. Technical decisions
Every decision, with the options considered and the trade-offs, is in the
**[decision log](docs/decision-log.md)**. Summary:

| Area | Choice | Why (short) |
|---|---|---|
| Agent approach | Function calling over deterministic Python tools | Exact numbers; personal data only reachable through verified order lookup; testable without a model |
| Policy retrieval | Full manual in a cached system prompt | 8 pages: no retrieval misses, least code |
| Model | Claude Haiku 5.5 (Sonnet 5.5 only if evals require it) | Cheapest current Claude model; quality measured, not assumed |
| Framework | Plain Anthropic SDK, hand-written tool loop | Nothing hidden; no beta dependency |
| Interface | Command line (`--debug`, `--save`, `--now`) | Fastest to build; example conversations are real transcripts |
| History | In memory, one session | Data minimisation under Brazil's data-protection law (LGPD) |
| Reviewer access | Hosted FastAPI proxy (default) or your own key | Reviewers don't need a key; the author's key never leaves the server |

## 5. Security & cost safeguards
_(planned; see [decision D15](docs/decision-log.md#d15))_

Layered protection for a US$5 prepaid API budget:
- A prepaid balance with no auto-reload.
- A US$3 monthly spend limit on the Anthropic workspace that holds the key.
- Keys only in environment variables, never in git; GitHub push protection is enabled.
- The proxy requires an access code.
- The proxy enforces its own model, length cap, system prompt and tool list, so it only works
  as this assistant.
- The proxy also limits request size, applies a global rate limit and a daily dollar budget.
- On the client side: limits on tool rounds per message, input length, and spend per session.
- Logs record no message content.

## 6. Deploying your own proxy
_(planned: Render Blueprint `render.yaml`, step-by-step)_

## 7. Assumptions
The data and the manual contradict themselves in places. Each case has one explicit rule (see
[decision D12](docs/decision-log.md#d12)). Where a rule is ambiguous, it is read in the
customer's favour (Brazil's Consumer Protection Code, CDC art. 47).
1. **What can be sold:** a product is sellable only if its status is `active` **and** it has
   stock.
   - The Giannini GF-3D (id 96) is "temporarily unavailable".
   - The Ibanez Bass 2X (id 136) is discontinued even though it shows stock.
   - The Kala barítono (id 130) is "coming soon".
2. **Contradictory product descriptions:** for products 135, 136, 137, 139, 140, 142 and 144,
   the free-text description names another brand or contradicts the specs. Those descriptions are withheld; the name, price,
   stock and specs are authoritative.
3. **Promotions:** only promotions marked active count. Promotions don't stack, and the 5% PIX
   discount never applies on top of a promotional price.
4. **Installments:** the detailed rules in §3.1 prevail over the summary table. Up to 3x, the
   minimum installment is R$ 50 (the manual's wording is ambiguous); 4–6x, R$ 80; 7–12x,
   R$ 100.
5. **Contact details:** phone/WhatsApp **(67) 3341-4444** and
   **contato@emporiodamusica.com.br**. §7 of the manual gives a different WhatsApp number, and
   one table spells the e-mail with an accent.
6. **Shipping:** an order of exactly R$ 500 ships free. The manual says free "above R$ 500" and
   charges a fee "below R$ 500", leaving R$ 500 itself undefined. Freight outside the Campo
   Grande area depends on the postcode and isn't quoted.
7. **Returns:**
   - The receipt date is taken as the order's estimated delivery date, the only date
     available.
   - Orders in the data are treated as online purchases, so the 7-day right to cancel applies.
   - Defective items are exchanged by the store within 30 days of purchase; after that, the
     store helps with the manufacturer's warranty.
8. **Order records are reported as they are.** Two order totals don't match their items, and
   three orders break the installment rules; the agent never "corrects" them.
9. **Stale orders:** if an order isn't delivered and its estimated delivery date has passed,
   the agent apologises and offers a human.
10. **Empty categories:** woodwinds, brass and orchestral strings have no products in the data.
    The agent says nothing is available right now, rather than claiming the store doesn't sell
    them.
11. **Holidays:** the manual says the store closes on holidays but doesn't list them, so the
    open/closed check ignores holidays.
12. **Identity check:** order details require the order number plus the e-mail or phone of
    that order's customer.

## 8. Known limitations & future work
_(to be completed)_
- The open/closed check ignores holidays (no holiday list in the manual).
- One e-mail address is shared by two customers in the data (ids 11 and 43), which weakens the
  identity check for that address.
- The free hosting tier sleeps when idle, so the first request can take about a minute.
- The proxy's usage counters are in memory and reset on restart; the Anthropic workspace spend
  limit is the persistent cap.
- **Future:** a local model (e.g. Qwen3 8B via Ollama, which accepts the same API format) as a
  zero-cost option; retrieval for the policies if the manual grows.

## 9. Testing & evaluation
Run `.venv\Scripts\python -m pytest`. Expected values were worked out by hand from the CSV files
and the manual, never copied from the code's output.

_(in progress)_
- **Unit tests (no model calls):** data loading, sellability, search filters, promotion and PIX
  maths, installments, order verification, no personal data in any tool output, store hours,
  fidelity of the manual transcription, and proxy limits.
- **Scenario evaluations:** about 15 scripted conversations run against the real model, with
  automatic checks and cost reported per model.

## 10. Example conversations
_(planned: 3–5 real transcripts in `examples/`)_

## 11. How AI coding assistants were used
**Tool:** Claude Code (Anthropic's AI coding assistant, Opus 5.5) in VS Code.

**Workflow** (rules in [`CLAUDE.md`](CLAUDE.md)): understand → research → plan → execute → test
→ document.
- **Understand:** Claude Code read the briefing, the policy manual and every CSV, and listed
  requirements, edge cases, security risks and every contradiction it found, separating facts
  from assumptions.
- **Research & plan:** in Claude Code's plan mode (where it can only read and propose, not
  change files), it researched options and checked prices and model retirements on official
  pages. Rael chose the options; the approved plans are in
  [`docs/implementation-plan.md`](docs/implementation-plan.md) and
  [`docs/implementation-plan-amendment-proxy.md`](docs/implementation-plan-amendment-proxy.md).
- **Execute & test:** one stage at a time. After each stage, Claude Code reports the changes,
  the real test output and the open issues, and suggests a commit. **Rael approves every
  commit.**
- **Document:** decisions are recorded in the [decision log](docs/decision-log.md) as they are
  made, with who decided.

**What the assistant did / what Rael did:** Claude Code did the reading, research, drafting and
coding. Rael made every product and technical decision, reviewed the files, and controlled the
budget, the credentials and the deployments.

## 12. Repository layout
```
emporio/   the agent package: cli.py, config.py, catalog.py (data and queries), rules.py
           (pricing, installments, opening hours)
knowledge/ politicas.md: verbatim Markdown transcription of the policy PDF (used in the prompt)
tests/     unit tests (pytest, no model calls)
data/      case data provided by Artefact (read-only, byte-identical)
docs/      implementation plans and decision log
CLAUDE.md  rules followed by the AI coding assistant
```
