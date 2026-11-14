# Source discovery: fresh sources for any place

Use it during onboarding (no guide, or a thin one), when a user moves, when they travel ("what's on in Eugene this weekend?"), and every couple of months to replace sources that went stale.

## Why this works anywhere
Every town has the same *kinds* of sources even though the names differ:

| Kind | Typical example | Good for |
|---|---|---|
| Alt-weekly / city paper calendar | the local weekly's events page | broadest coverage |
| Tourism board / "things to do" | visit-the-city events page | festivals, annual events |
| Parks, libraries, museums | city parks and rec calendar | daytime, free, classes, families |
| College & community radio | the campus station's concert calendar | small local shows |
| DIY / small rooms | all-ages spaces, house-show lists, record-store in-stores | the alt / punk / weird stuff |
| Community threads & newsletters | the city subreddit's weekend thread, a local email roundup | what locals actually go to |
| Multi-city platforms | Bandsintown, DICE, Resident Advisor, Eventbrite, Meetup | touring acts, electronic, niche groups |
| Venue calendars | the rooms that keep showing up in the above | the most reliable dates |

## Steps
1. `lsa sources discover` (add `--place 'Eugene, OR'` for a trip or a move). It prints a categorized search plan built from the place and the user's ranked interests.
2. Run the searches (in parallel). For each candidate source, open it:
   - **Keep it** only if it has *dated listings for the next two weeks*, covers this place (not just the nearest big city), and fits an interest or covers everything locally.
   - **Access mode:** `fetch` if the page reads cleanly; `search` if it blocks bots or is JS-only; `browser` if it needs a real browser; `app` if it's an app or Instagram the user checks themselves.
   - **Priority:** 1 = check every run, 2 = usually, 3 = if time.
3. **Venues fall out of sources.** Rooms that show up across several kept sources and match an interest are venue candidates. Propose them with an area and interests.
4. **Show the user** a short table (name, covers, access, priority) and ask which to keep. Add the ones they keep to `sources` with `found_by: discovery` (and the venues to `venues`), via `profile-updates.md`.
5. **Trips:** don't change the profile for a one-off trip. Use the discovered sources for that run only, and score with `lsa evaluate --no-window` against the user's taste (distance won't mean much away from home; say so).

## Keeping sources fresh
- During every research run, note sources that refused, returned nothing current, or only had last year's dates.
- Record that in `sources[].notes` and `last_ok`. After two dead runs, propose dropping or demoting the source and running discovery for a replacement.
