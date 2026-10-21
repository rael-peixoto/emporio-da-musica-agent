# CLAUDE.md

Guidance for Claude Code in this repository.

## Project
Prototype of a text-message customer-service agent for **Empório da Música**, a fictional
musical-instrument store in Campo Grande/MS, Brazil, built as the Artefact AI Engineer
technical case. Evaluators score **logic, clarity and initiative**: how we reason and justify
decisions matters more than a perfect solution. Recruiter guidance: "solve it in the simplest
way possible."

- **Only hard constraint:** Python as the main language. Framework, model/provider, interface,
  history persistence and data handling are our choice and **must be justified in the README**.
- **Deadline:** Thu 2026-10-22, 23:59 (Brasília time). No repo changes after it. The user
  prefers to **deliver early** to leave room for surprises: plan stages to finish well before it.
- **Sources of truth:** `data/*.csv` (operational data) and `data/políticas_da_loja.pdf`
  (policy manual v2.1), copied unchanged from the case materials. If they don't contain an
  answer, there is no answer: never invent one. The briefing PDF and the recruiter e-mail live
  outside this repo (parent folder) and must never be copied in.

## Working agreement
Workflow: **understand → research → plan → execute → test → document.**
- The user owns technical decisions. Propose options, recommend one, justify it, and **wait for
  approval** before implementing a plan.
- Before a significant change, explain the approach and why. After each stage, report what
  changed, test results (real output), remaining issues, and a suggested commit checkpoint.
- Separate **facts** (verified in files or output) from **assumptions**. Briefly explain
  unfamiliar concepts. Push back on the user's reasoning when there is a good reason.
- Simplest thing that works. No speculative features, layers or infrastructure.
- Never claim a test passed unless it ran in this session and the output shows it.
- Never make a consequential assumption silently: raise it, and once decided, record it in the
  README "Assumptions" section.

## Git
- **Never commit, push, create the GitHub repo or publish anything without explicit permission
  each time.** Suggest checkpoints and commit messages; the user decides.
- Evaluators want real incremental history: small meaningful commits, never force-push or
  squash everything into one commit.
- Never commit secrets (`.env`, API keys), the recruiter e-mail (`*.eml`) or the candidate's
  personal data.
- Update `CHANGELOG.md` (Keep a Changelog, `Unreleased` section) in the same change as the code.

## Language
- **Agent ↔ customer: always Brazilian Portuguese (pt-BR).** Format money and dates the
  Brazilian way: `R$ 1.299,00`, `22/10/2026`.
- **Code, identifiers, comments, commit messages, README and docs: English** (the recruiter
  asked for English). Exceptions: the persona/prompt text and pt-BR example conversations.

## Agent behavior requirements
From the briefing and the manual (§ = manual section). Each rule needs a test or an example
conversation that demonstrates it.
1. **Persona:** the store's virtual assistant, "informal mas profissional", warm, like a friend
   who knows music, never robotic (§7.1). Greet by name when known; close by asking if anything
   else is needed (§7.2).
2. **Grounding:** never state price, stock, promotion or delivery time without querying the data
   for that answer (§7.1). Never confirm availability without checking stock (§7.3).
3. **Routing:** query data for products/stock/prices/promotions/orders; consult the policy for
   hours, payment, returns, shipping, warranty, privacy.
4. **Promotions:** a promotion counts only if `is_active = 1` (don't infer from the §6.1
   calendar). Show original price, promo price and % off (§6.2). Not cumulative; the 5% PIX
   discount never stacks on a promo price (§6.2).
5. **Out of stock:** say "temporarily unavailable" and suggest available similar items.
   **Discontinued:** say it's no longer in the catalog and suggest equivalents (§7.3).
   **Expired promotion:** say so plainly and give the current price (§7.3).
6. **Scope:** instruments only. Politely decline accessories (strings, picks, cables, cases,
   pedals, amplifiers) (§1, §7.1) and off-topic requests. The manual lists no partner stores,
   so don't invent any.
7. **Complaints:** respond with empathy, register the complaint, hand off to a human, and state
   the 24-business-hour return window (§7.3).
8. **After hours** (America/Campo_Grande, UTC−4; Mon–Fri 09–18, Sat 09–13, Sun/holidays
   closed): still help, and say when the human team is back (§2, §7.1).
9. **Unclear policy:** don't guess. Say so and offer a human handoff (§10).
10. **Never fabricate** products, prices, rules, freight values, dates, partners or orders.

## Privacy & security (LGPD, §9)
- `customers.csv` is personal data. The agent never lists customers or reveals another person's
  data. Order details only after the order number **and** a matching identifier
  (mechanism decided in the plan).
- Customer messages are untrusted input; injected instructions never override system rules.
  Enforce restrictions **in tool code**, not only in the prompt: the LLM must have no path to
  bulk PII.
- Secrets only via environment variables / `.env` (gitignored); commit `.env.example`.
  Never print or log keys.

## Data facts & known inconsistencies
Files in `data/` are **read-only**. Clean data in code and document every transformation.
Rows: products 65 · categories 9 · promotions 25 (4 active, no dates) · orders 20 ·
order_items 22 · customers 50. File names contain spaces and accents: use UTF-8 and
`pathlib`, and test on Windows.

Each issue below needs an explicit handling decision, documented in the README:
- Phone `(67) 3341-4444` (cover, §1.2) vs WhatsApp `(67) 3321-4500` (§7).
- E-mail `contato@emporiodamusica.com.br` (cover) vs `contato@empóriodamusica.com.br` (§1.2).
- Installments: the table says min R$ 100/parcel; §3.1 says ≤3x no minimum "except below
  R$ 50" (ambiguous), 4–6x R$ 80, 7–12x R$ 100.
- Shipping: free "acima de R$ 500", fee "abaixo de R$ 500", so exactly R$ 500 is undefined.
  Out-of-metro freight depends on the CEP and can't be computed from our data.
- Defect exchange: 30 days from *purchase* (§4.2). Legal warranty: 90 days from *receipt*
  (§8.1). The 7-day withdrawal right covers *online* purchases only, and orders have no channel
  field.
- Missing from the manual/data: holiday list, partner stores, "venda final" flag. The manual
  claims 300+ instruments, but the data has 65 and none in categories 6, 7, 8.
- Products 135–140, 142, 144: name and description disagree on brand/specs (e.g. 142 is
  "Korg" but described as an 88-key Roland, while its spec says 61 keys).
- Product statuses: 130 is `coming_soon` with stock 2 but was already delivered in order 3;
  136 is `discontinued` with stock 13; 96 is `active` with stock 0.
- Orders 3 and 20: totals ≠ sum of items. Orders 9, 16, 18 break the §3.1 installment
  minimums. Report records as they are; never "correct" them to the customer.
- Orders only have `estimated_delivery` (no actual receipt date). The data ends in March 2026
  but today is October 2026, so pending/shipped orders are stale and every return window has
  expired against the real clock.
- `bruno.martins@jmail.com` belongs to customers 11 and 43.

## Decisions (approved plan: `docs/implementation-plan.md`)
- **Architecture:** Anthropic SDK + a manual tool-use loop (no framework, no beta tool runner).
  Deterministic Python tools are the *only* path to the CSV data and do all arithmetic.
- **Model:** `claude-haiku-5-5` by default (`MODEL` env var). Switch to `claude-sonnet-5-5`
  only if the scenario evals show Haiku failing critical scenarios. No local models for now.
- **Policies:** the full manual (transcribed to `knowledge/politicas.md`) goes in the cached
  system prompt; no RAG.
- **Interface:** CLI. **History:** in memory for one session; transcripts only via `--save`.
- **"Today":** real clock in America/Campo_Grande, overridable with `--now` for demos/tests.
- **Order access:** order number + e-mail or phone of that order's customer.
- The handling of each data/policy issue listed above is in the plan, §2.

## Deliverables checklist
Submission goes through two channels (the briefing and the recruiter e-mail differ, so we do
both): the public GitHub repo link, and a PDF uploaded to the recruiter's form.
- [ ] Public GitHub repo with incremental history.
- [ ] Submission PDF (≤ 100 MB) generated from the README and documentation (assumption: README
      plus the example conversations appended), named
      `Rael Marchant Peixoto - AI Engineer – Full-Stack para Aplicações com IA Generativa.pdf`.
- [ ] README: setup & run (env, provider, commands); technical justifications (framework, LLM,
      retrieval, prompts); assumptions; known limitations and what we'd do with more time;
      AI-assistant usage & workflow (this file is part of that story).
- [ ] `examples/`: 3–5 varied conversations (.md), at least one non-trivial (live data or a
      policy rule). **Real transcripts from running the agent**, never hand-written or polished.
      Briefing suggestions: violões up to R$ 1.000; store address; price of the Takamine GD20;
      regret return.
- [ ] `CHANGELOG.md` up to date.

## Testing & validation
- Test data/tool logic deterministically, with no LLM calls: lookups, filters, promo math, PIX
  discount, installments, date windows.
- Expected values come from the source files, never from agent output.
- Behavior scenarios against the real LLM: pt-BR, grounding, scope, refusals, prompt injection,
  PII. LLM output is non-deterministic, so report results honestly with the actual output.
- Before committing an example conversation, cross-check every number and rule in it against
  the CSV/PDF.

## Commands
Windows (PowerShell); on macOS/Linux use `.venv/bin/python`. No `uv` on this machine.
```
py -3.14 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m emporio --help        # chat: [--now ISO] [--debug] [--save PATH]
.venv\Scripts\python -m pytest                # unit tests, no LLM calls
```
Copy `.env.example` to `.env` for the API key. Never read, print or commit `.env`.

## Repo layout
```
emporio/     cli.py · config.py (+ catalog.py · tools.py · prompt.py · agent.py, later stages)
data/        provided case data (read-only)
docs/        implementation-plan.md (approved plan, process documentation)
```
