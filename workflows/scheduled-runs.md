# Scheduled runs

Scheduled runs happen with nobody watching, may not load personal skills, and may have different tools. So each one gets a **self-contained prompt** rendered from the profile.

```
lsa schedule list
lsa schedule render weekend-digest --target local
lsa schedule render weekend-digest --target cloud
```

Tasks: `weekend-digest`, `tonight`, `month-ahead`, `log-check`.

## Local vs cloud
| | Local scheduled task (Claude desktop app) | Cloud routine |
|---|---|---|
| Runs when | the computer is on and the app is running | always |
| Reads the profile and log | yes (uses the CLI) | no: the prompt carries an inline brief |
| Logs picks / dedups | yes | no |
| Web fetch | usually works | some event sites refuse cloud fetches; the prompt says to fall back to search |
| Notion / push | if connected | if connected to the routine |
| After profile changes | nothing to do | **re-render and update the routine** |

## Setting one up (do it for them; don't make them paste prompts)
1. **Agree what it delivers.** Ask once: email the full digest to themselves? Add picks to their calendar automatically (Top only, or all picks)? Push notification? Switch those on in the profile (`automation.email_digest`, `automation.calendar`, `integrations.push`) and record their email in `user.email`. These are standing opt-ins they're giving you; say so plainly.
2. **Agree a time.** Friday early afternoon is a good default. Use a `CRON_TZ=<their timezone>` prefix so it stays in local time across daylight saving.
3. **Cloud routine (runs with the computer off):**
   - `lsa schedule routine weekend-digest --cron '<cron>'` prints the create body and the connectors it needs (`_attach_connectors`: Notion for their guide, Gmail for the email, Google Calendar for auto-add).
   - Get the environment id and the connectors' `connector_uuid`/`name`/`url` from the routines tool (an existing routine's `mcp_connections`, or the connector list). Add them to `mcp_connections`, add each connector's tools to `allowed_tools` (e.g. `mcp__Gmail__*`), drop the `_` keys, then create it.
   - If a needed connector isn't connected, tell them where to connect it rather than creating a routine that will fail.
4. **Local scheduled task (computer on):** create it with the scheduled-task tool using `lsa schedule render weekend-digest --target local`.
5. **Reply to add (optional):** if they want to reply to the email to add picks, set `automation.email_digest.reply_to_add: true`, re-render the digest routine, and create a second routine with `lsa schedule routine reply-handler --cron 'CRON_TZ=<zone> 15 6-20/2 * * 5,6,0'` (Gmail + Google Calendar only).
6. **Record it** in `automation.schedules[]` (`task`, `when`, `target`, `routine_id`) and offer one test run now, so they see the email and calendar entries before Friday.

## Rules baked into every prompt
Read/research/report only: no tickets, RSVPs, messages to anyone, sign-ups, guide edits or personal data. The only exceptions are the user's own digest email and their own calendar, and only when they switched those on. Time never removes an event. Verify dates; label unverified items; don't retry refused fetches; say when a tool is missing.
