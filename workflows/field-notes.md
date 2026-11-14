# Field notes: logging what happened, learning from it

The log is how picks get better. Keep it light: one line from the user is enough.

## Recording
- Find the row: `lsa log list` (or `--status suggested going`).
- Not in the log yet (they found it themselves)? Normalize it and `lsa log add --events-file - --status went`.
- Record the outcome:
  ```
  lsa log update <id> --status went --rating 4 --return yes --people-met 'Sam (climbing), the door guy' --note 'great room, loud'
  ```
  Statuses: `suggested`, `interested`, `going`, `went`, `skipped`, `missed`, `cancelled`. Rating 1–5. Return: yes / no / maybe.
- People: first names and context only, and only what they tell you.

## Learning
`lsa insights` summarizes outcomes per interest and per venue and suggests profile changes, e.g.:
- raise an interest they keep going to and rating highly
- lower one they're always pitched and always skip
- add a venue they'd go back to; flag one they wouldn't

Present suggestions as proposals. Apply only what they agree to, via `profile-updates.md`.

## Their own notes
If their guide has a field-notes table (e.g. in Notion), you may offer to add the entry there too. That's an edit to their guide: show the exact row first and wait for an explicit yes.
