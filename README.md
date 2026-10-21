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
| Tools, prompt, agent loop, command-line chat (direct mode) | Done |
| Hosted proxy (FastAPI on Render) and proxy mode | Built and tested locally; deployment pending |
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
You need Python 3.11+ (developed on 3.14). Two ways to run it, both using the same agent code:
- **A. Hosted proxy (default, no API key needed):** you run the agent locally, and its model
  calls go through the author's proxy. You need the access code sent with the submission. It
  is not published here, to protect the API budget.
- **B. Your own Anthropic API key (direct mode):** the agent calls Anthropic directly.

If `ANTHROPIC_API_KEY` is set, direct mode is used; otherwise the proxy is. `LLM_BACKEND=proxy`
or `LLM_BACKEND=direct` in `.env` forces a mode. The chat prints which mode is active.

```
git clone https://github.com/rael-peixoto/emporio-da-musica-agent.git
cd emporio-da-musica-agent
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt     # Windows
# .venv/bin/python -m pip install -r requirements.txt       # macOS / Linux
copy .env.example .env                                        # macOS / Linux: cp
```
Edit `.env` and fill in **either** `EMPORIO_ACCESS_CODE` (option A) **or** `ANTHROPIC_API_KEY`
(option B), then start the chat:
```
.venv\Scripts\python -m emporio                   # chat in the terminal; type "sair" to quit
.venv\Scripts\python -m emporio --debug           # also show tool calls, tokens and cost
.venv\Scripts\python -m emporio --now 2026-02-20T10:00 --save conversa.md
```
- `--now` simulates another date/time in Campo Grande. The order data ends in March 2026, so
  this is how to see an order still inside its return window.
- `--save` writes the conversation, including every tool call, to Markdown.

**Cost:** about US$0.001–0.002 per customer message on Claude Haiku 5.5. In a measured run,
the 8,246-token cached prompt was written once and then read from cache on every later call.

In proxy mode, the first message may take up to a minute if the free server was asleep; the
chat shows a "Conectando ao servidor..." message while it wakes.

## 3. How it works
```
                ┌─ direct:  Anthropic SDK ──────────────────────────► api.anthropic.com
CLI ─► agent ──┤            (your own key)
 (local tools, └─ proxy:   Anthropic SDK, base_url=Render URL ─► FastAPI proxy ─► api.anthropic.com
  local data)              api_key = access code                (key kept server-side)
```
- **Agent loop** (`emporio/agent.py`): Claude decides whether to answer directly or call a
  tool. Tools run locally in Python over the CSV files and return exact, pre-formatted values
  (e.g. `"R$ 2.199,00"`), so the model never does arithmetic.
  - At most 5 tool rounds per message; the last round forbids tools, so the model has to
    answer.
- **Tools** (`emporio/tools.py`):

  | Tool | What it does |
  |---|---|
  | `buscar_produtos` | Product search by term, category, price range, string type or electric/acoustic; prices include active promotions |
  | `detalhes_produto` | Specs, availability, list price, active promotion, PIX price, maximum interest-free installments |
  | `listar_categorias` | Categories with their count of available products |
  | `consultar_pedido` | Order status, items, tracking and computed policy deadlines; **requires the order number plus the customer's e-mail or phone**, and returns only the first name |
  | `registrar_atendimento_humano` | Hands the case to a human and returns a protocol number |

- **Prompt** (`emporio/prompt.py`, in pt-BR):
  - The static part (about 8k tokens) holds the persona, the ground rules, how to handle
    common situations, the interpretation notes (see [Assumptions](#7-assumptions)), and the
    full policy manual. It is cached.
  - A small second block carries the current date/time and whether the store is open, so the
    cache stays valid between calls.

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
The project runs on a US$5 prepaid API budget, so protection is layered. Decisions
[D13–D15](docs/decision-log.md#d13) explain why.

| Layer | Measure | What it prevents |
|---|---|---|
| Anthropic account | Prepaid balance, auto-reload off | Absolute ceiling of US$5 |
| Anthropic workspace | US$3 monthly spend limit | Persistent cap, even if the proxy restarts |
| Secrets | API key only in Render's environment variables and a local `.env` (gitignored, including `.env.*`); GitHub push protection detects Anthropic keys | Key leaks |
| Proxy: access | Access code (random, 256-bit) compared in constant time, sent as `x-api-key` or `Authorization: Bearer` | Strangers using the budget |
| Proxy: pinning | The server replaces the model (Haiku 5.5), effort, `max_tokens`, system prompt and tool list with its own copies; the client supplies only the conversation and a small date/time block (≤ 600 chars) | Using the proxy as a free general-purpose Claude endpoint; expensive models; long outputs |
| Proxy: limits | Body ≤ 512 KB; ≤ 100 messages; user text ≤ 1,500 chars; global 30 requests/min (`429`); US$1/day estimated budget (`403`, checked *before* calling Anthropic) | Token stuffing, bursts, slow drains |
| Proxy: errors | Upstream key or spend-limit errors are returned as a generic `503` | Leaking account details |
| Client | ≤ 5 tool rounds per message; ≤ 1,500 characters per message; session ends at 50 turns or US$0.50 estimated | Runaway loops (this also protects reviewers' own keys) |
| Privacy | Proxy logs record tokens and cost only: no message content and no IP addresses (uvicorn's access log is off) | Personal data in logs (LGPD) |

**Not done:** per-IP rate limiting. Render's `X-Forwarded-For` header can be spoofed by the
client, so it would give false assurance.

**Known gap:** the proxy's counters live in memory and reset when the free instance restarts.
The Anthropic workspace limit is the persistent backstop.

## 6. Deploying your own proxy
The proxy is `proxy/app.py` (FastAPI). [`render.yaml`](render.yaml) is a Render Blueprint for
the free plan.
1. **Anthropic Console:** set a monthly spend limit on the workspace and create an API key.
2. **Render:**
   - Sign in with GitHub → **New → Blueprint** → select this repository.
   - When asked for `ANTHROPIC_API_KEY`, paste the key. `EMPORIO_ACCESS_CODE` is generated
     automatically (a random 256-bit value).
   - Deploy. Render installs `proxy/requirements.txt` and runs
     `uvicorn --factory proxy.app:create_app --no-access-log`; `/health` is the health check.
3. Copy the service URL into `PROXY_URL`, and give reviewers the access code privately
   (`EMPORIO_ACCESS_CODE` in their `.env`).

Optional environment variables: `PROXY_DAILY_BUDGET_USD` (default 1.00),
`PROXY_REQUESTS_PER_MINUTE` (default 30), `PROXY_MODEL`, `PROXY_EFFORT`.

To run it locally (for example, to test proxy mode):
```
set EMPORIO_ACCESS_CODE=<a-long-random-test-code>   # PowerShell: $env:EMPORIO_ACCESS_CODE="..."
.venv\Scripts\python -m uvicorn --factory proxy.app:create_app --port 8765 --no-access-log
```
The proxy also needs `ANTHROPIC_API_KEY` in its environment. Then run the chat with
`LLM_BACKEND=proxy`, `PROXY_URL=http://127.0.0.1:8765` and the same code.

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
emporio/   the agent package
           cli.py      terminal chat (--now, --debug, --save)
           agent.py    tool-use loop and cost guards
           tools.py    tools the model can call
           prompt.py   system prompt (static and cached, plus current context)
           llm.py      API client (direct or proxy) and cost estimation
           catalog.py  data loading and queries
           rules.py    pricing, installments, opening hours
           config.py   settings and usage limits
knowledge/ politicas.md: verbatim Markdown transcription of the policy PDF (used in the prompt)
proxy/     app.py: FastAPI proxy that holds the API key server-side (deployed on Render)
tests/     unit tests (pytest, no model calls)
render.yaml  Render Blueprint for the proxy
data/      case data provided by Artefact (read-only, byte-identical)
docs/      implementation plans and decision log
CLAUDE.md  rules followed by the AI coding assistant
```
