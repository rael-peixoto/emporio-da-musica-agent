# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Project scaffold: `emporio` package with CLI options (`--now`, `--debug`, `--save`) and
  configuration (`MODEL`, `EFFORT`, store time zone); pinned runtime and dev requirements;
  `.env.example`.
- `docs/implementation-plan.md`: the approved implementation plan, including model research.
- `CLAUDE.md`: project guidelines for Claude Code (workflow, git rules, agent behavior
  requirements, privacy rules, known data and policy inconsistencies, deliverables).
- `data/`: case materials (CSV tables and the store policy manual), copied unchanged.
- `.gitignore` for secrets, Python artifacts and recruiter correspondence.
- `.gitattributes` so `data/` is stored without line-ending conversion.
