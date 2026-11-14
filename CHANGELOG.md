# Changelog

All notable changes are listed here. Versions follow [semantic versioning](https://semver.org).

## 0.2.0 (2026-11-14)
- **Source discovery** (`lsa sources discover [--place ...]`, `workflows/source-discovery.md`): a categorized search plan built from any place and the user's ranked interests (alt-weekly, tourism board, parks/libraries, college and community radio, DIY spaces, community threads, multi-city platforms, per-interest). Vetting rules, access modes, and a freshness loop. Onboarding uses it when a user has no guide; the skill uses it for moves and trips.
- **Early birds and busy mornings:** `weekend.latest_start` (hard cutoff), `weekend.prefer_daytime` (evening starts score lower), and blocking standing plans (`anchors[].start/end/blocks`) that exclude clashing events. Recurring events respect both.
- Sources gain `notes`, `last_ok`, `found_by`. Schema stays v1 (all additions optional).
- 99 tests.

## 0.1.0 (2026-11-14)
First release.
- Onboarding skill (`/local-scene-setup`): adaptive interview that reads an existing scene guide (Notion page, doc, list) first, then asks only what's missing; approval step; installs the personal skill.
- Profile schema v1: ranked interests, area map with travel times, excluded places, weekend definition, constraints, budget, venues with closed/verify status, sources with access modes, standing plans, recurring and annual events, fallbacks, rules of thumb, scoring, digest settings, knowledge base, locked approval keys, automation.
- Engine (`lsa`): weekend/tonight/N-day windows, recurring-rule parser, research plans, explainable scoring, dedup, digests with push line, event log with ratings and insights, local and cloud scheduled-task prompts, paths-only skill generation.
- Six hypothetical profiles and 86 tests, including cross-context and privacy checks.
