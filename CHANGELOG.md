# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] - 2026-10-22

First complete release, delivered for the Artefact AI Engineer case. Entries are grouped by
type; the commit history shows the step-by-step order.

### Added
- `python -m emporio.setup`: saves the access code (hidden input) or your own API key to
  `.env`, so reviewers never edit files by hand. The private PDF page shows the ready-to-paste
  command.
- README "Tech stack at a glance" table: each technology, what it does, and why it was chosen
  over the alternatives.
- Screenshot of a harder conversation (gift recommendation and a promotion question), plus two
  more: privacy and honesty (refusing another customer's contact data; an honest "not found"),
  and maths with no invented facts (instalments on a promotion; no made-up warranty period).
- Evaluation scenario `contatos`; the suite is 23/23 (US$0.0106). 134 unit tests.
- Decision log D28 and D29, plus an observation added to D11 (follow-ups use the session
  memory).
- Local web chat (`python -m emporio.web`, D26):
  - A WhatsApp-style chat tab with suggestion chips.
  - A "behind the scenes" console tab with tool calls, data, tokens and cost.
  - It uses the same agent in direct or proxy mode, runs on `127.0.0.1` only, and protects its
    API with a per-launch page token.
  - README screenshots in `docs/img/`.
- README future work: a concrete design for a real WhatsApp integration (D27).
- `--mode proxy|direct` CLI flag, which works the same in cmd and PowerShell (unlike setting
  environment variables).
- README: plain-language explanation of the automated checks; a note that proxy users get
  prompt changes only after a Render redeploy; "Things to try" rows for contacts and a
  product that isn't found.
- Prompt: when a product isn't found, suggest available alternatives in the same category.
- Proxy deployed on Render at `https://emporio-proxy.onrender.com`, now the default
  `PROXY_URL`. Verified end to end:
  - a real chat through Render;
  - a wrong access code gets a friendly error at no cost;
  - a request asking for Opus, 50,000 tokens and its own system prompt still got Haiku, a
    capped reply and the store persona.
- README "Things to try": a CLI test guide covering every feature. Decision log D23 and D24.
- `scripts/build_pdf.py`: builds the submission PDF (README + decision log + examples) with
  headless Chrome; repo-relative links become GitHub links. An optional private
  reviewer-access page reads the code from `.env`. Output goes to `dist/` (gitignored).
- `examples/`: five real, unedited transcripts (catalogue, store information, prices and
  promotions, a verified return with a human handoff, scope and privacy). Every R$ amount was
  checked automatically against the data.
- pt-BR enforcement: a mid-conversation `system` reminder after each customer message, plus a
  code guard that re-asks once when a reply looks English. The `idioma` scenario went from 3/5
  to 10/10. The proxy accepts only that exact reminder as a `system` message. Decision log D21.
- Evaluation scenario `regras_de_parcelamento`; the suite is now 22 scenarios, 22/22 on Haiku
  5.5 (US$0.0110).

### Changed
- Contacts (D28): the agent gives only WhatsApp (67) 3321-4500. The other number and the
  e-mail are masked in the model's copy of the manual, and so is the §3 table's "parcela mínima
  de R$ 100,00" (the §3.1 tiers prevail). Example 2 was regenerated.
- WhatsApp number (D25): the agent gives WhatsApp (67) 3321-4500 (§7) and phone
  (67) 3341-4444; the conflict is flagged in the README.
- The session cost line is shown only with `--debug`.
- Language (D23): pt-BR by default; an English question may be answered in English. Removed
  the mid-conversation reminder and the English-detection guard. The proxy again rejects any
  client `system` message.
- Prompt fixes from the example review (D22): the §3.1 installment tiers are spelled out; no
  deadlines the manual doesn't define; never mention tools or internal instructions to
  customers.
- The complaint scenario now covers a two-message flow (the agent may ask for the order
  first).
- Scenario evaluations (`evals/`): 21 scripted conversations against the real model, with
  checks for required and forbidden values, tool calls and language. Claude Haiku 5.5:
  21/21, US$0.0097 (`evals/results/claude-haiku-5-5.md`, with transcripts). Decision log D20.
- Hosted proxy for reviewers (`proxy/app.py`, FastAPI), which keeps the API key server-side:
  - Exposes `POST /v1/messages`, so the agent's standard SDK client only changes its base URL.
  - Access code in `x-api-key` or `Authorization: Bearer` (Anthropic SDK 2.0 sends the
    latter), compared in constant time.
  - Replaces the model, effort, `max_tokens`, system prompt and tool list with the server's
    own copies.
  - Limits on body, message and user-text size; global rate limit (429 with `retry-after`);
    daily US$ budget checked before calling Anthropic (403); generic 503 for upstream
    key/limit errors; metadata-only logs.
- `render.yaml` (Render Blueprint, free plan), `.python-version`, `proxy/requirements.txt`.
- `tests/test_proxy.py` (18 tests, fake upstream). Verified end to end against a local proxy
  with a real Haiku call; the proxy log showed tokens and cost but no content.
- README: both quick-start modes, the security and cost safeguards table, and proxy deployment
  steps.
- The agent, working in direct mode:
  - `emporio/tools.py`: five tools (search, details, categories, verified order lookup with
    computed policy deadlines, human handoff); no tool output contains customer contact data.
  - `emporio/prompt.py`: cached pt-BR system prompt with the rules, interpretation notes and
    the full manual, plus a per-call date/time and opening-hours block.
  - `emporio/agent.py`: manual tool loop with limits (5 tool rounds, 1,500-character input,
    50 turns or US$0.50 per session). Failed calls leave the history intact, and truncated or
    refused replies are handled.
  - `emporio/llm.py`: client for direct and proxy mode; cost estimates from API usage.
  - CLI chat with `--debug` (tool calls, tokens, cost) and `--save` (Markdown transcript).
- Tests for tools, prompt, mode selection and the agent loop (with a fake model client):
  99 tests in total.
- `.env.example` documents both modes; decision log D19 (fixes from the first live run).
- `knowledge/politicas.md`: verbatim Markdown transcription of the policy manual (tables kept
  as tables), and `tests/test_policy_fidelity.py`, which requires the same numbers and the same
  vocabulary as the PDF in both directions, so a typo, an invented rule or a dropped passage
  fails the build.
- Data layer: `emporio/catalog.py` loads the CSVs into typed records, keeps the best active
  promotion per product, withholds contradictory descriptions, filters searches with
  promotional prices and typo-tolerant terms, and verifies orders by e-mail or phone.
  Customer records are reachable only through that verified lookup.
- Business rules: `emporio/rules.py` (exact Decimal money, promotion and PIX pricing, §3.1
  installment tiers, R$ formatting, opening hours and next opening).
- Unit tests (`tests/test_catalog.py`, `tests/test_rules.py`): 52 tests, with expected values
  worked out by hand from the CSVs.
- Decision log entries D17 (workspace spend limit) and D18 (standing commit permission).
- `README.md` skeleton whose sections map to the delivery requirements (setup, technical
  decisions, assumptions, limitations, AI-assistant workflow), with a progress table.
- `docs/decision-log.md`: dated timeline of decisions D1–D16, with options, trade-offs and who
  decided.
- `docs/implementation-plan-amendment-proxy.md`: approved design for the hosted FastAPI proxy,
  direct mode, and cost/abuse safeguards.
- Project scaffold: `emporio` package with CLI options (`--now`, `--debug`, `--save`) and
  configuration (`MODEL`, `EFFORT`, store time zone); pinned runtime and dev requirements;
  `.env.example`.
- `docs/implementation-plan.md`: the approved implementation plan, including model research.
- `CLAUDE.md`: project guidelines for Claude Code (workflow, git rules, agent behavior
  requirements, privacy rules, known data and policy inconsistencies, deliverables).
- `data/`: case materials (CSV tables and the store policy manual), copied unchanged.
- `.gitignore` for secrets, Python artifacts and recruiter correspondence.
- `.gitattributes` so `data/` is stored without line-ending conversion.

### Fixed
- Asking for a specific out-of-stock or discontinued model no longer risks a "not in the
  catalogue" reply: when a name search finds nothing sellable, `buscar_produtos` returns the
  matching unavailable items with their status.
- The list of products with contradictory descriptions is 135, 136, 137, 139, 140, 142, 144.
  Earlier docs said "135–140", but 138 ("StingRay") names a model of its own brand.

### Changed
- The cost safeguards use a US$3 spend limit on the existing Anthropic workspace instead of a
  dedicated workspace (decision D17).
