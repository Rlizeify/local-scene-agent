# Profile generation: answers → profile.yaml

Schema: `{{ENGINE_ROOT}}/schemas/user-profile.schema.json`. Annotated example: `{{ENGINE_ROOT}}/configuration/example-profile.yaml`. Always finish with `lsa profile validate`.

## Mapping

| They said / their guide shows | Goes to |
|---|---|
| "I live in X", "about 20 min to downtown" | `home.base`, `home.areas[]` (`name`, `places`, `minutes`) |
| "Nothing in Y, ever" | `home.excluded_places` (hard filter) |
| "I'll drive an hour for something great" | `home.max_drive_minutes: 60` (farther still shows, scored low) |
| Ranked interests | `interests[]` with `weight` 5→1 by rank |
| Genres, formats, words in a listing | `interests[].keywords` (lowercase; specific beats generic: "hard techno" over "music") |
| Favorite rooms | `interests[].venues`, plus a `venues[]` entry with `area` and `status` |
| Artists / promoters / crews they follow | `interests[].artists`, `interests[].promoters` |
| "Not big-room EDM" | `interests[].avoid_keywords: [big room]` (drops just that interest's match) |
| "Never anything with X" | top-level `avoid_keywords` (excludes the event) |
| Venue closed / "verify" | `venues[].status: closed` (excluded) / `verify` (scored lower, flagged) |
| Walk-in, no-ticket places | `fallbacks[]` (or `venues[].walk_in: true`) |
| Weekly class / session they always do | `anchors[]` (`label`, `day`, `time`, `where`) |
| "First Friday art walk", "every Thursday" | `recurring[]` with `rule` the engine parses: `every <day>`, `first|second|third|fourth|last <day>` (or 1st/2nd/3rd/4th) |
| Annual festivals | `annual[]` with `months` |
| Calendars / aggregators | `sources[]`: `access` fetch / search / browser / app; `priority` 1 (always) – 3 (if time) |
| Their own guide (Notion/Doc) | `knowledge_base[]` with `type`, `ref` (page id or URL), `use_for` |
| Late nights fine | `weekend.late_nights: true` |
| "In bed by 8" | `weekend.bedtime: "20:00"` (soft: later things rank lower with a heads-up) |
| "Saturdays 7–noon I surf" | `anchors[]` with `day`, `start`, `end` (soft: clashes flagged, not hidden) |
| "Nothing political" (a theme, not a word) | `avoid_themes[]` |
| "Email me the list" / "put picks on my calendar" | `user.email`, `automation.email_digest`, `automation.calendar` |
| Budget | `budget.comfortable_max`, `budget.hard_max` (hard filter), `free_bonus` |
| 21+ ok / kids along | `constraints.max_age_limit_ok: 21` / `0` + `kid_friendly_only: true` |
| Rules of thumb | `goals.operating_rules[]` (Claude applies these in judgement) |
| "Recurring beats one-off" | also `goals.prefer_recurring: true` (+0.5 to recurring events) |
| Digest preferences | `digest.*` |
| Automate it | `automation.schedules[]` (`task`, `when`, `target`), `notify`, `integrations` |

## Scoring defaults (tune later from `lsa insights`)

```yaml
evaluation:
  pick_threshold: 6
  top_threshold: 8
  criteria:
    - {id: interest, weight: 4}   # how well it matches what they love, scaled by that interest's rank
    - {id: distance, weight: 2}   # travel time vs their map
    - {id: venue, weight: 1}      # one of their rooms / in their directory
    - {id: price, weight: 1}
    - {id: timing, weight: 1}     # late starts, earliest_start
    - {id: novelty, weight: 1}    # from the log: places they loved vs said "never again"
```

- **Explorers:** raise `novelty` to 2. **Homebodies:** raise `distance` to 3.
- **"The drive is not a reason":** lower `distance` to 1 and raise `max_drive_minutes`.
- **Custom criteria** need `positive_signals` / `negative_signals`, e.g. `{id: solo_friendly, weight: 1, positive_signals: [open mic, class, workshop, meetup, jam], negative_signals: [bottle service, vip table]}`.
- **Caps / adjustments** use the same rule format as hard filters: `{field: price_min, op: gt, value: 60, max_score: 7, reason: "pricey, never top-tier"}`. Fields: any event field (`title`, `venue`, `city`, `price_min`, `age_limit`, `start_hour`, `day`, `tags`, `description`) or a key in `event.extra`.

## Rules
- Never store a street address, phone number, or the reason behind a sensitive rule unless offered.
- A venue's `area` must be one of `home.areas[].name`.
- Interest ids are short slugs (`edm`, `jazz`, `kids_outings`); venues/sources/recurring entries reference them in `interests`.
- Add anything unknown to `gaps`. Remove the starter blocking gaps once filled.
- Log every change after the first draft with `lsa profile touch --change '...'`.
