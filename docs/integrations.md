# Integrations

Everything is optional. With none, the agent still works from web search plus your profile. See [`configuration/integrations.example.yaml`](../configuration/integrations.example.yaml).

| Integration | Used for | Setup | Without it |
|---|---|---|---|
| Web search | Finding listings, the fallback when sites block fetches | Built into Claude | Only `fetch` sources and your guide |
| Web fetch | Reading calendars and event pages | Built into Claude | Search snippets only (more `unverified`) |
| Built-in browser / Claude in Chrome | JS-heavy calendars (ticketing apps, some venue sites) | Desktop app / Chrome extension | Those sources fall back to search |
| Notion connector | Reading your scene guide each run (`knowledge_base.type: notion`) | Authorize Notion in your Claude app | Profile only; re-sync by hand |
| Google Docs / Drive | Same, for a Google Doc guide | Authorize in your Claude app | Same |
| Calendar (read) | Avoiding clashes ("you're busy Saturday night") | Authorize, set `permissions.may_read_calendar: true` | Not checked |
| Push notifications | One-line digest alert | Claude desktop/mobile app | Read the digest |
| Scheduled tasks / routines | Unattended digests | Claude desktop app / claude.ai | On demand only |

## Never stored here
No API keys, tokens, passwords or OAuth credentials. Connectors are authorized and held by your Claude app. Nothing in this repo needs a `.env`.

## Writing to integrations
Adding a calendar event, editing your Notion guide, sending a message: always shown first and done only on your explicit yes (see [safety.md](safety.md)).
