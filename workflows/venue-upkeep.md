# Venue upkeep: keeping the directory honest

Scenes change fast. Venues close, rename, or change what they book.

## When you notice something during research
- **A venue looks closed** (closure post, dead calendar, "permanently closed" listing): propose `status: closed`. Closed venues are excluded from digests.
- **Unsure:** propose `status: verify`, with a note on what you saw and when.
- **Renamed:** add the old name to `aliases`.
- **A new place that fits their taste** (shows up repeatedly in their top interests): propose adding it with an `area` and `interests`.
- **A new reliable source:** propose adding it to `sources` with an access mode and priority.

## Applying
1. Show the exact YAML change.
2. On their yes, edit the profile, `lsa profile touch --change '<what>'`, re-validate, and ask for re-approval (`lsa profile approve` after their explicit yes).
3. Their own guide (Notion page, doc) is theirs. You may offer the same change there, but only make it after showing the exact edit and getting a separate yes.
