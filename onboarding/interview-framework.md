# Interview framework

This is a map, not a script. Ask what this person needs, in this order, and skip what their material already answers.

**Each group has three parts:**
1. **Must learn:** the core facts.
2. **Ask if relevant:** follow-ups triggered by earlier answers.
3. **Done when:** the condition to move on.

## A. Where you are (always first; short)
**Must learn:**
- Name / preferred name
- Home base: neighborhood or town (never a street address) and timezone
- How they get around: car, transit, bike, rideshare
- The areas they'd go to, each with a rough one-way travel time ("downtown ~20 min, the next city over ~45")
- The farthest they'll usually go for something great

**Ask if relevant:**
- **New to town:** how new, and is meeting people a goal? (This feeds `goals` and favors recurring, solo-friendly things.)
- **Transit / no car:** last train or bus home; that becomes an `earliest_start` / late-night rule and a distance cap.
- **Anywhere they never want to go:** a neighborhood, a city, a venue. These become `excluded_places` (hard filter). Don't ask why.

**Done when:** you could draw their map with travel times.

## B. What they're into (this builds the ranking)
**Must learn:**
- The 3–7 kinds of things they'd leave the house for: music genres, comedy, art, sports, outdoors, food, markets, classes, community, nightlife, family outings...
- **The rank order.** Ask them to put them in order, or pick a #1. Top ≈ 5, next ≈ 4, and so on down to 1.
- For each: keywords that identify it in a listing (genres, formats), favorite rooms/places, artists/teams/promoters they follow.
- Anything inside a category they don't want (e.g. "electronic, but not big-room EDM", "comedy, but not open mics").

**Ask if relevant:**
- **Music:** genres and sub-genres in their own words; 3–5 artists; standing vs seated; big rooms vs small.
- **Daytime people:** markets, hikes, surf/skate, classes, sports leagues. Mark these `daytime: true`.
- **Active hobbies** (climbing, running, surfing, skating): the gyms/clubs/spots and any group sessions; these often become standing plans.
- **Families:** kids' ages; nap windows; stroller/kid-friendly; that sets `constraints`.

**Done when:** you could pick their top 3 from a stack of 50 listings and explain each.

## C. Rhythm and limits
**Must learn:**
- Which nights count as "the weekend" (default Friday 5pm to Sunday night) and whether late nights (10pm+ starts) are normal for them
- Budget per ticket: comfortable, and a hard max if they have one; whether free stuff deserves a bump
- Age limits they meet (21+? kids along?)
- Who usually comes along: solo, partner, friends, family
- Standing weekly plans that should always show (a class, a run club, a weekly session)

**Ask if relevant:**
- **Sober or sober-curious:** prefer alcohol-free settings? (Never assume; ask only "any settings you'd rather avoid?")
- **Accessibility needs:** seating, step-free access, quiet spaces.
- **Morning people:** nothing before X / nothing after Y.

**Done when:** you know what an ideal and an acceptable weekend look like.

## D. Goals and rules of thumb
**Must learn:**
- What they want out of this: discover new things, go deeper into a scene, meet people, get out more, plan dates, keep the kids busy...
- Their own rules of thumb. Ask: "Any rules you go by?" Examples: "recurring beats one-off", "go alone", "the drive is not a reason to skip", "check the venue's Instagram the day of", "no more than one late night a weekend".

**Ask if relevant:**
- **Meeting people:** favor recurring events and small rooms (`prefer_recurring: true`).
- **Explorers:** favor novelty (raise the `novelty` criterion weight).

**Done when:** you could explain why you'd rank a small recurring night over a big one-off show, or the reverse, for this person.

## E. Where to look
**Must learn:**
- The calendars, aggregators, venue pages, newsletters and apps they already trust
- Their own guide, if any (Notion page, doc), to read every run
- Anything that's closed or questionable in their lists

**Ask if relevant:**
- **No sources:** search the area yourself ("<city> events calendar", "<city> <genre> listings", local alt-weekly, tourism board, ticketing platforms popular there) and propose 6–12 sources ranked P1–P3. Mark sites that need a browser or block bots as `access: search`.
- **App-only sources** (Instagram, Bandsintown, ticketing apps): record as `access: app` so the digest can remind them to check.

**Done when:** at least one source per top interest.

## F. Digest and automation
**Must learn:**
- How many top picks (default 3), how long (default ~40 lines), and the tone ("phone-scannable, no fluff")
- Whether to show travel times
- Whether they want it automated: which day/time, and where (see `docs/scheduled-tasks.md`): a local scheduled task (can use the full engine) or a cloud routine (runs even when the computer is off; uses an inline brief)
- Notifications: always, only when there are picks, never

**Done when:** you could write the scheduled prompt.

## Wrap-up checks before step 4
- Every top interest has keywords **and** at least one room or source.
- Every venue's area matches one of the home areas.
- Recurring events have a rule the engine understands ("every saturday", "first friday", "3rd saturday", "last saturday").
- No street addresses, phone numbers or reasons for sensitive rules are stored unless the user offered them.
