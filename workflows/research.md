# Research: finding what's on

Goal: a list of real, dated candidates for the window, weighted toward what the user loves most.

## 1. Get the plan
`lsa plan` (add `--tonight` or `--days N`). It prints:
- the window (dates/times)
- the user's guide(s) to read first (`knowledge_base`)
- sources in priority order with how to access each
- targeted web searches built from their top interests, rooms and artists
- venues to skip (closed) and to double-check (verify)

`lsa window` adds standing plans, recurring events that fall in the window, and annual events coming up.

## 2. Read their guide first (read-only)
If `knowledge_base` lists a Notion page or doc, fetch it (Notion fetch tool, load via ToolSearch if deferred). It may have newer venues, closures or sources than the profile. **Never edit it.** If it disagrees with the profile (a venue closed, a new source), note it for `venue-upkeep.md` at the end.

## 3. Cover the sources
Work P1 → P2 → P3 until you have enough, or time runs short.
- **`access: fetch`:** read the page (web fetch, or the built-in browser if available). Pull every event in the window.
- **`access: search`:** the site blocks bots or is JS-only. Use web search: `"<source or venue> <Month Day>"`, `"<venue> this weekend"`.
- **`access: browser`:** use a browser tool if this session has one; otherwise fall back to search and say so.
- **`access: app`:** you can't check it. Add a one-line reminder at the end ("check Bandsintown / their IG").
- **A refused fetch:** don't retry it. Switch to search.
- **Run independent searches in parallel.** Prefer standard search mode; go deeper only when results look thin or stale.

## 4. Verify dates
- Every candidate needs **this year's date** inside the window. Search results surface last year's pages constantly; check the year and the weekday match.
- `verified: true` only if you saw the date on the event's own page (venue, promoter or ticketing). Aggregator-only or snippet-only = `verified: false`.
- Recurring nights ("every Saturday"): confirm it's still running if you can; if not, `verified: false`.

## 5. Normalize to JSON
One object per event (schema: `schemas/event.schema.json`):
```json
{"title": "Artist / Night name", "venue": "Room", "city": "Town",
 "start": "2026-11-14T22:00", "price_min": 25, "price_text": "$25-40", "age_limit": 21,
 "tags": ["techno"], "url": "https://...", "source": "Resident Advisor", "verified": true,
 "recurring": false, "description": "one or two lines from the listing"}
```
- `start` without a time (`"2026-11-14"`) is fine when the time isn't posted.
- `tags`: genre/format words from the listing; they drive interest matching. Add `interests: ["<id>"]` only when you're sure and the listing's words wouldn't match.
- Don't guess prices or age limits. Leave them out.

Save the list to `<data>/digests/candidates-<date>.json`, then go to `digest.md`.
