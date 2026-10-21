# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
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
