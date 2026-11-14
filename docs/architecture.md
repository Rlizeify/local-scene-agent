# Architecture

Part 1 audits the single-user setup this project was extracted from. Part 2 describes how it was rebuilt as a reusable, location-agnostic framework. Part 3 explains which pieces were borrowed from the sibling project it's modeled on.

---

## Part 1: Audit of the original setup

The original was one person's "what should I do this weekend" system, built from three pieces and no code:

| # | Piece | How it worked | Classification |
|---|---|---|---|
| 1 | **A scene guide in Notion** | One long page: standing weekly plans, ~26 event calendars and aggregators (with notes on what each covers), recurring nights (first Fridays, weekly art walks), annual festivals sorted near → far, venue lists by region and drive time (with closed / verify notes), scene-specific sections (promoters, local bands, groups), walk-in fallbacks, a 90-day plan, personal rules of thumb, and an empty field-notes table. | The *structure* is universal. Every entry is personal. → profile sections: `sources`, `venues`, `recurring`, `annual`, `anchors`, `fallbacks`, `goals.operating_rules`, `knowledge_base`. |
| 2 | **A weekly cloud routine** | Friday afternoon, a scheduled Claude run with a long prompt: who and where (home base, drive times, one hard "never go here" rule), a ranked list of six interests with keyword lists and favorite rooms, the sources to hit, how to handle sites that refuse cloud fetches (fall back to search), "verify the date is this weekend", an output format (Top 3 with why, then sections in rank order, each line day · time · act · venue · price · age), and one push notification. | The mechanism is reusable; the prompt was the profile in disguise. → `schedule.py` renders the same prompt from any profile. |
| 3 | **Claude's judgement** | Each run, Claude ranked by reading the prompt's preferences. | Kept, but now on top of a deterministic, explainable rule score. |

### Weaknesses fixed in the rebuild
- **Preferences lived in a prompt.** Changing taste meant editing prose in a routine. They're now a schema-validated profile with a changelog and re-approval.
- **No memory.** The routine couldn't know what was already suggested, attended, loved or hated. There's now a log with dedup, ratings, "would I go back", and `insights` that proposes weight changes.
- **Recurring events were text.** "First Friday" had to be noticed by Claude each week. The engine now places recurring events on the calendar deterministically.
- **Closed venues were notes.** "⚠️ closed, verify" in prose. Now `status: closed | verify` is enforced (excluded / flagged).
- **Ranking was opaque.** Every score now has a per-criterion explanation and a list of unknowns.
- **Cloud-only.** The routine couldn't touch local files. There are now two scheduled targets (local with full engine, cloud with an inline brief) and an on-demand skill.

---

## Part 2: The generalized architecture

```
            ┌──────────────────────────────┐
  user ───▶ │  Skill: local-scene-setup    │  first run / profile updates
            │  (onboarding interview)      │  reads their existing guide if any
            └──────────────┬───────────────┘
                           │ writes + user approves
                           ▼
            ┌──────────────────────────────┐
            │  Layer 2: User configuration │  <home>/users/<id>/profile.yaml
            │  (schema-validated YAML)     │  taste · map · rhythm · rules · sources
            └──────────────┬───────────────┘
                           │ lsa skill install
                           ▼
            ┌──────────────────────────────┐
  user ───▶ │  Skill: local-scene[-<id>]   │  generated from a generic template;
            │  (Layer 3: execution)        │  holds PATHS only, reads profile at runtime
            └──────┬───────────────┬───────┘
     on demand     │               │  lsa schedule render (local | cloud)
                   ▼               ▼
            ┌──────────────────────────────┐
            │  Layer 1: Core engine (lsa)  │  window · recurring · plan · evaluate ·
            │  + workflow playbooks        │  digest · log · insights · schedule
            └──────────────────────────────┘
                           │
                           ▼
            <home>/users/<id>/  log.csv · history.jsonl · digests/ · documents/
```

### Layer 1: Core engine (`src/localscene_agent/`, `workflows/`)
Deterministic work in Python; judgement in markdown playbooks Claude follows.

| Capability | Deterministic (CLI) | Judgement (playbook) |
|---|---|---|
| Date window | `lsa window` (weekend / `--tonight` / `--days N`, per-profile weekend definition) | — |
| Recurring + annual | rule parser (`every saturday`, `first friday`, `last saturday`, seasonal months) | `plan-ahead.md` |
| Research plan | `lsa plan`: sources by priority and access mode, targeted searches from top interests/rooms/artists, closed and verify lists | `research.md`: fetching, search fallback, date verification |
| Scoring | `lsa evaluate`: hard filters → weighted criteria → adjustments → caps, with explanations and unknowns | `evaluation.md`: fit score from rules of thumb and the specific ask |
| Dedup | same title + venue + day collapses (digest and log) | — |
| Digest | `lsa digest`: Top N, standing plans, sections by interest rank, recurring, coming up, fallback, push line | `digest.md`: wording, misranks |
| Memory | `lsa log` (atomic CSV, backups), `lsa insights` | `field-notes.md`, `venue-upkeep.md` |
| Scheduling | `lsa schedule render <task> --target local|cloud` | `scheduled-runs.md` |

The engine deliberately **doesn't scrape**. Event sites change weekly and many block bots; Claude reads them with whatever tools the session has (fetch, search, browser), and the engine makes everything around that deterministic.

Nothing in Layer 1 names a city, genre, venue or price. Domain specifics ("21+", "no bars", "after bedtime", "the drive is not a reason") are profile data: hard filters, caps, custom criteria, weights.

### Layer 2: User configuration (`schemas/user-profile.schema.json`)
One YAML file per user: `user`, `home` (areas with travel minutes, excluded places), `weekend`, `constraints`, `budget`, ranked `interests` (keywords, rooms, artists, promoters, per-interest exclusions), `avoid_keywords`, `venues`, `sources`, `anchors`, `recurring`, `annual`, `fallbacks`, `goals`, `evaluation`, `digest`, `knowledge_base`, `permissions` (approval keys locked by the schema), `automation`, `gaps`, `changelog`.

A profile must be `approved` (by the user, in conversation) before digests run or a skill is installed. Any edit drops it back to draft.

### Layer 3: Execution (`skills/local-scene/SKILL.md.tmpl`)
The template is rendered with **paths only**. At runtime the skill validates and reads the live profile, so edits apply immediately. Several users on one machine get separate data folders and skills (`local-scene-alex`, `local-scene-sam`) on one engine.

---

## Part 3: What was borrowed from the job-search sibling

This repo mirrors the three-layer design of a sibling project (a self-configuring job-search agent): onboarding skill → approved profile → generated paths-only skill → CLI engine + playbooks, with schema-locked approvals, a privacy fingerprint test, and scheduled-task prompt rendering. The domain logic is new: windows and recurring rules instead of postings, taste-weighted interest matching instead of title/pay matching, an attendance log with ratings instead of an application tracker, and a cloud-brief target because the original weekend automation ran as a cloud routine.
