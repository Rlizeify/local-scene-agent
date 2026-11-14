# Scheduled tasks

## Supported tasks
| Task | What it does | Suggested time |
|---|---|---|
| `weekend-digest` | Researches the weekend, ranks, writes the digest, one push | Friday early afternoon |
| `tonight` | Tonight only | Weekdays ~4pm, if wanted |
| `month-ahead` | Annual festivals, big shows and on-sale dates for the next 5 weeks | First of the month |
| `log-check` | Lists last weekend's picks so you can record what you did | Monday morning |
| `reply-handler` | Reads your replies to the digest ("add 2 and 5", "remove the symphony"), updates your calendar, replies to confirm | Every 2 hours Fri–Sun, e.g. `CRON_TZ=<zone> 15 6-20/2 * * 5,6,0` |

Render a prompt, or a ready-to-create cloud routine:
```bash
lsa --user <id> schedule render weekend-digest --target local
lsa --user <id> schedule render weekend-digest --target cloud
lsa --user <id> schedule routine weekend-digest --cron 'CRON_TZ=America/New_York 0 14 * * 5'
```
`schedule routine` prints the body the routines tool needs (name, cron, prompt, model, tools) and lists the connectors to attach. The `/local-scene` skill fills in the environment and connectors and creates it, so nobody has to paste prompts by hand.

## What a run delivers
- **The digest**, ranked by your interests: Top picks, standing plans, one section per interest, recurring events, coming up, sources.
- **An email with the whole digest** (optional, `automation.email_digest`): sent to your own inbox only. It opens with what was added to your calendar and "Want any of these on your calendar too?".
- **Calendar entries** (optional, `automation.calendar`): Top picks (or all picks) added to your own calendar, marked free, no guests, no duplicates, labeled so you can delete what you skip.
- **One push notification** (optional).
- **Reply to add** (optional, `automation.email_digest.reply_to_add` + a `reply-handler` routine): the "want these too?" picks are numbered, and the email ends with a short CALENDAR OPTIONS list. Reply "add 2 and 5" and the reply handler puts them on your calendar and replies "[scene-bot] Added: ...". It only acts on replies sent from your own address, only adds or removes the digest's own `[Scene]` entries, and only replies to you.

## Two targets, honestly compared
| | `local`: Claude desktop app scheduled task | `cloud`: claude.ai routine |
|---|---|---|
| Needs the computer on | yes | no |
| Uses the engine, profile and log | yes, via the CLI | no; carries an inline brief |
| Dedups against what was already suggested | yes | no |
| Saves digests to `digests/` | yes | no; the run's final message is the digest |
| Web fetch | usually fine | some event sites refuse cloud fetches; the prompt falls back to search |
| Notion guide | if the connector is available to scheduled runs | if the connector is attached to the routine |
| Push notification | if available | if available |
| After profile edits | nothing to do | **re-render and update the routine** |

## Limits (both targets)
- **No approvals possible.** Prompts forbid buying, RSVPs, sign-ups, messages, guide edits and entering personal data.
- **Personal skills may not load** in scheduled runs, so prompts are self-contained and don't depend on `/local-scene`.
- **Tools differ from interactive sessions.** Prompts tell Claude to say when web search, a browser, Notion or push wasn't available, instead of pretending.
- **Timezones.** Cloud cron expressions should carry a timezone (e.g. `CRON_TZ=America/New_York`). Local tasks use the computer's clock.

## Migrating an existing hand-written routine
If you already have a weekend routine with your taste written into its prompt (as the original setup did), onboarding can read that prompt as source material. Afterwards, replace the routine's prompt with `schedule render weekend-digest --target cloud`, so taste lives in one place: your profile.
