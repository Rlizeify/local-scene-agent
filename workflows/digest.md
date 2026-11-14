# Digest: the weekend list

## Build it
```
lsa digest --events-file <candidates.json> --save --log --source 'RA' --source 'Venue calendars'
```
- `--save` writes `digests/<date>-weekend.md` (with the push line in a trailing comment).
- `--log` adds every top/pick to `log.csv` as `suggested`; duplicates are skipped, so re-running is safe.
- `--json` returns the markdown, the push line, counts and (with `--verbose`) every score breakdown.

Layout (from the profile's `digest` settings):
1. **Top N** across all interests, each with a one-line "why".
2. **Standing plans** that fall in the window.
3. **One section per interest**, in the user's ranked order, only if it has something.
4. **Recurring this weekend** from the profile (not already listed).
5. **Coming up:** annual events this month and next.
6. **No-plan fallback** when fewer than 3 things made it.
7. **Sources.**

## Polish it (your part)
- Rewrite the "why" lines in plain words tied to *their* taste ("the techno room you keep going back to"), not scoring jargon.
- Fix obvious misranks using their rules of thumb, and say so in one line at the bottom.
- Keep it under `digest.max_lines`. Cut maybes before picks.
- Keep every `(unverified)` label. Add "check the venue's IG day-of" for late, volatile nights if that's one of their rules.
- Add reminders for `access: app` sources you couldn't check.

## Notification
The engine prints a push line under 200 characters starting with `digest.push_prefix`. Send it only when the profile allows (`automation.notify` and `integrations.push`), and only one.

## Afterwards
If they say they're going to something: `lsa log update <id> --status going`. If they want tickets: show the exact page and price, and wait for an explicit yes before anything else.
