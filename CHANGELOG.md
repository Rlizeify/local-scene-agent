# Changelog

All notable changes are listed here. Versions follow [semantic versioning](https://semver.org).

## 0.1.0 (2026-11-14)
First release.
- Onboarding skill (`/local-scene-setup`): adaptive interview that reads an existing scene guide (Notion page, doc, list) first, then asks only what's missing; approval step; installs the personal skill.
- Profile schema v1: ranked interests, area map with travel times, excluded places, weekend definition, constraints, budget, venues with closed/verify status, sources with access modes, standing plans, recurring and annual events, fallbacks, rules of thumb, scoring, digest settings, knowledge base, locked approval keys, automation.
- Engine (`lsa`): weekend/tonight/N-day windows, recurring-rule parser, research plans, explainable scoring, dedup, digests with push line, event log with ratings and insights, local and cloud scheduled-task prompts, paths-only skill generation.
- Six hypothetical profiles and 86 tests, including cross-context and privacy checks.
