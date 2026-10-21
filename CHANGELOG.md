# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- `examples/`: five real, unedited transcripts (catalogue, store information, prices and
  promotions, a verified return with a human handoff, scope and privacy). Every R$ amount was
  checked automatically against the data.
- pt-BR enforcement: a mid-conversation `system` reminder after each customer message, plus a
  code guard that re-asks once when a reply looks English. The `idioma` scenario went from 3/5
  to 10/10. The proxy accepts only that exact reminder as a `system` message. Decision log D21.
- Evaluation scenario `regras_de_parcelamento`; the suite is now 22 scenarios, 22/22 on Haiku
  5.5 (US$0.0110).

### Changed
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
- The list of products with contradictory descriptions is 135, 136, 137, 139, 140, 142, 144.
  Earlier docs said "135–140", but 138 ("StingRay") names a model of its own brand.

### Changed
- The cost safeguards use a US$3 spend limit on the existing Anthropic workspace instead of a
  dedicated workspace (decision D17).
