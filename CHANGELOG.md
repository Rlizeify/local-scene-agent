# Changelog

All notable changes are listed here. Versions follow [semantic versioning](https://semver.org).

## 0.4.0 (2026-11-14)
- **Reply to add:** with `automation.email_digest.reply_to_add`, the digest numbers its extra picks and ends with a CALENDAR OPTIONS block; the new `reply-handler` task (`lsa schedule routine reply-handler`) reads replies sent from the user's own address ("add 2 and 5", "remove the symphony"), updates their calendar, labels the reply, and confirms in-thread. Without it, the email says to ask /local-scene instead of promising replies.
- Cloud briefs now carry each source's access mode and notes, so runs search instead of fetching sites known to block them.

## 0.3.0 (2026-11-14)
- **Time is never a filter.** `weekend.latest_start` is replaced by `weekend.bedtime` (+ `late_penalty`): late starts and late endings rank lower with a heads-up. Standing plans with `start`/`end` flag clashes ("during Surfing: you'd leave early") and cost `conflict_penalty` (default 0.5) instead of hiding events; `anchors[].blocks` is removed. Recurring events carry heads-ups instead of disappearing. Migration: rename `latest_start` to `bedtime` and drop `blocks`.
- **`avoid_themes`:** themes to skip that keywords can't catch, judged by Claude and carried into scheduled prompts.
- **Email digest** (`automation.email_digest`): scheduled runs email the full digest to the user's own inbox, opening with what was added to the calendar and what else they might want there.
- **Calendar auto-add** (`automation.calendar`): opt-in standing approval to add Top picks (or all picks) to the user's own calendar, marked free, no guests, deduplicated, verified times only by default.
- **Routine builder:** `lsa schedule routine <task> --cron ...` prints a ready-to-create cloud routine body with the connectors it needs; the skill creates it, no pasting.
- Events accept an `end` time. 103 tests.

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
