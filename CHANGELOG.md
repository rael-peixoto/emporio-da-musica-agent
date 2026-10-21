# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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
