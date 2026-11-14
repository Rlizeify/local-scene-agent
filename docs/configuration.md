# Configuration

Your profile is `~/.local-scene-agent/users/<id>/profile.yaml`. The onboarding interview writes it; you can edit it by hand. After editing:
```bash
lsa --user <id> profile touch --change 'what you changed'
lsa --user <id> profile validate
lsa --user <id> profile approve
```
The fully annotated example is [`configuration/example-profile.yaml`](../configuration/example-profile.yaml); six more are in [`examples/hypothetical-profiles/`](../examples/hypothetical-profiles/).

## The parts that drive ranking

### Interests (the big one)
```yaml
interests:
  - id: techno
    label: Techno & house          # becomes a digest section heading
    weight: 5                      # rank: top ≈ 5, last ≈ 1
    keywords: [techno, house, acid, warehouse]
    venues: [Small Room, Other Room]       # favorite rooms: strong match + venue bonus
    artists: [Some DJ]                     # followed artists/promoters: strongest match
    promoters: [Some Crew]
    avoid_keywords: [edm]                  # cancels THIS interest's match only
```
An event's interest score = match strength (keywords < favorite room < followed artist) × the interest's rank. Its best interest picks its digest section.

### The map
```yaml
home:
  base: Neighborhood, City
  max_drive_minutes: 60            # beyond this, distance scores 0 (not excluded)
  areas:
    - {name: Home, places: [Neighborhood, Next Neighborhood], minutes: 10}
    - {name: Downtown, places: [Downtown, City], minutes: 25}
  excluded_places: [Somewhere]     # hard filter
```
Venues in your directory carry an `area`, so events at known rooms always land on the map even if the listing's city is vague.

### Criteria weights
| id | What it measures |
|---|---|
| `interest` | match to what you love, scaled by rank |
| `distance` | travel time on your map |
| `venue` | your rooms / your directory / marked verify |
| `price` | vs. comfortable and hard max |
| `timing` | late starts (unless `late_nights`), `earliest_start` |
| `novelty` | from your log: loved it, skipped it, "never again", new |
| custom | any id with `positive_signals` / `negative_signals` |

### Rules: hard filters, caps, adjustments
Same shape; fields are any event field (`title`, `venue`, `city`, `price_min`, `age_limit`, `start_hour`, `day`, `tags`, `description`) or a key in `event.extra`. Ops: `contains_any`, `not_contains_any`, `equals`, `in`, `not_in`, `lt`, `lte`, `gt`, `gte`, `missing`.
```yaml
evaluation:
  hard_filters:
    - {field: start_hour, op: gte, value: 19, reason: after bedtime}
  caps:
    - {field: price_min, op: gt, value: 60, max_score: 7, reason: pricey, never top-tier}
  adjustments:
    - {field: day, op: equals, value: sunday, points: -1, reason: Sundays are for resting}
```

### Built-in hard filters
Excluded places, venues marked `closed`, top-level `avoid_keywords`, age limit above `constraints.max_age_limit_ok`, cheapest ticket over `budget.hard_max`, outside the window.

### Built-in bonuses
+0.5 for recurring events when `goals.prefer_recurring`; +0.3 for free events when `budget.free_bonus`. Events matching none of your interests are capped at 4.

## Calendar pieces
- `anchors`: standing weekly plans (always shown).
- `recurring`: `rule` is `every <day>`, `first|second|third|fourth|last <day>` (or 1st/2nd/3rd/4th), optional `months` for seasonal ones.
- `annual`: `months`; shown under "Coming up" this month and next.
- `fallbacks`: no-plan, walk-in options shown when a weekend is thin.

## Sources and your own guide
```yaml
sources:
  - {name: City alt-weekly, url: https://..., access: search, priority: 1, interests: [indie]}
knowledge_base:
  - {type: notion, ref: <page id>, title: My scene guide, use_for: [venues, sources]}
```
`access`: `fetch` (readable page), `search` (blocks bots / JS-only), `browser`, `app` (you check it; the digest reminds you). The knowledge base is read each run and **never edited** without your yes.
