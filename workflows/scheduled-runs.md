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

## Setting one up
1. Render the prompt with the target the user wants.
2. Show it, and agree a time (Friday early afternoon is a good default for a weekend digest).
3. Create the task with the scheduled-task tool (local) or the routines tool (cloud), if this session has them. Otherwise give them the prompt and the steps.
4. Record it in the profile: `automation.schedules[]` with `task`, `when`, `target`.

## Rules baked into every prompt
Read/research/report only: no tickets, RSVPs, messages, sign-ups, guide edits or personal data. Verify dates; label unverified items; don't retry refused fetches; say when a tool is missing.
