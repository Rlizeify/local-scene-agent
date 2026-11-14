# Local Scene Agent

A self-configuring "what should I do this weekend, where I live?" agent for Claude. It interviews you like a well-connected local friend, saves your taste, your map and your rules as a structured profile, and installs a personal `/local-scene` skill. From then on, without you explaining yourself again, it can:
- research this weekend (or tonight) and hand you a short, ranked list built around what *you* love
- tell you whether a specific show, flyer or listing is worth it
- look ahead at festivals and on-sale dates
- remember where you went and how it was, so picks get better
- run every Friday on a schedule

It works anywhere and for anyone: a techno kid in Brooklyn, a family in Austin, a contra dancer in rural Vermont, a sober maker in Seattle. Nothing in the engine assumes a city, genre, venue, budget or bedtime. All of that lives in your profile.

**It recommends; you act.** It never buys tickets, RSVPs, contacts anyone, edits your notes or shares your data without your explicit yes. It never invents lineups, times or prices. See [docs/safety.md](docs/safety.md).

## How it works
```
/local-scene-setup ──interview──▶ profile.yaml ──lsa skill install──▶ /local-scene
 (onboarding skill)              (your taste)                         (your personal skill)
                                                                            │
                         lsa engine (window · recurring · plan · evaluate · digest · log · schedule)
```
- **Layer 1, core engine:** a small Python CLI (`lsa`) plus workflow playbooks. It works out the weekend window, places your recurring events on the calendar, builds a research plan from your top interests, scores every candidate with explanations, dedupes, writes the digest and push line, keeps a log of what you went to, and renders scheduled-task prompts. It doesn't scrape; Claude does the reading with whatever tools it has.
- **Layer 2, your configuration:** one schema-validated YAML profile: ranked interests (keywords, favorite rooms, artists), your map with travel times, no-go places, budget, age limits, standing plans, recurring and annual events, sources, your own scene guide (Notion/Doc, read-only), rules of thumb, digest style. Versioned, with re-approval.
- **Layer 3, execution:** a personal skill generated from a generic template. It holds *paths only* and reads your live profile every run, so on-demand use and scheduled runs share one engine.

Full design: [docs/architecture.md](docs/architecture.md).

## Quick start
```bash
git clone https://github.com/<you>/local-scene-agent.git
cd local-scene-agent
python -m pip install -e .          # or: pip install -r requirements.txt
python lsa.py skill install-onboarding
```
Then in Claude Code (CLI, desktop app or IDE), type **`/local-scene-setup`**. It takes 10–15 minutes; point it at any guide or venue list you already keep. At the end you approve your profile and it installs **`/local-scene`**.

Afterwards:
```
/local-scene what should I do this weekend?
/local-scene anything good tonight?
/local-scene is this worth it: https://...
/local-scene what festivals are coming up next month?
/local-scene I went to the Saturday show, 5/5, would go back
/local-scene that venue closed, take it off
/local-scene set up a Friday 2pm digest
```
Or just ask about your weekend; the skill triggers on its own.

## What a digest looks like
```
# Your weekend: Fri Nov 13 – Sun Nov 15

## Top 3
1. Fri 8pm · Vocal jazz quartet: standards night · Yoshi's, Oakland · from $28 · 21+ — https://...
   _why: Live jazz; Oakland, ~20 min; one of your rooms_
2. Sat 7:30pm · Four-band punk bill · 924 Gilman, Berkeley · from $12 · (unverified) — https://...
   _why: Punk & DIY shows; Berkeley, ~20 min; one of your rooms_
3. Sat 4pm · Makers market and night market · Jack London Square · free · (unverified)

## Standing plans
- Sat 08:00 Saturday morning run club · Lake Merritt

## Repertory film
- Sun 6pm · 35mm double feature · The New Parkway, Oakland · from $12

## Recurring this weekend
- Sun 16:00 · Sunday jazz jam · a bar in Temescal

PUSH: Weekend picks: Vocal jazz quartet (Fri); Four-band punk bill (Sat); Makers market (Sat)
```
(From the fictional example profile and test fixtures.)

Details: [installation](docs/installation.md) · [configuration](docs/configuration.md) · [scheduled tasks](docs/scheduled-tasks.md) · [integrations](docs/integrations.md) · [safety](docs/safety.md) · [testing](docs/testing.md)

## Repository layout
```
lsa.py                    run the engine without installing (skills call this)
src/localscene_agent/     engine: profile, window, events, evaluate, research, digest, log,
                          schedule, skillgen, cli
schemas/                  user-profile, event and log-row JSON Schemas
onboarding/               the onboarding skill: SKILL.md, interview framework, profile mapping
skills/local-scene/       generic personal-skill template (SKILL.md.tmpl)
workflows/                playbooks: research, evaluation, digest, tonight, plan-ahead,
                          field notes, venue upkeep, scheduled runs, profile updates
configuration/            annotated example profile and integrations config
examples/                 six hypothetical users in very different places and lives
tests/                    engine, onboarding, profile validation, cross-context, privacy
docs/                     architecture, installation, configuration, scheduling,
                          integrations, safety, testing
```

## Requirements
- **Python 3.10+**, with PyYAML and jsonschema.
- **Claude Code**, or the Claude desktop app with skills.
- **Optional:** web search and a browser tool (better coverage), a Notion or Google Docs connector (to read your own guide), push notifications, scheduled tasks or routines.

## Versioning
[Semantic versioning](https://semver.org). Profiles carry `schema_version`; a breaking schema change bumps the major version and ships a migration note in [CHANGELOG.md](CHANGELOG.md). Generated skills record the engine version; regenerate with `lsa skill install --force` after upgrading.

## Related
Built on the same three-layer pattern as a sibling self-configuring job-search agent: onboarding interview → approved profile → generated paths-only skill → CLI engine.

## License
MIT. See [LICENSE](LICENSE).
