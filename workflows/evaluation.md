# Evaluation: is this worth going to?

## The rule score (deterministic)
`lsa evaluate --events-file <file>` (or `-` for stdin). Add `--no-window` for an event outside the current weekend.

Pipeline:
1. **Hard filters → `excluded`:** excluded places, venue marked closed, top-level avoid-keywords, age limit above `constraints.max_age_limit_ok`, cheapest ticket over `budget.hard_max`, outside the window, and the profile's `evaluation.hard_filters`.
2. **Weighted criteria (each 0–1; unknown = 0.5 and listed in `unknowns`):**
   - `interest`: best-matching interest × that interest's rank. Keyword hits, favorite rooms and followed artists/promoters all count; an interest's own `avoid_keywords` cancels it.
   - `distance`: travel time from the user's area map (≤15 min = 1.0, sliding to 0.2 at `max_drive_minutes`, 0 beyond).
   - `venue`: one of their rooms (1.0), in their directory (0.8), marked verify (0.5).
   - `price`: free (1.0) down to 0 at the hard max.
   - `timing`: late starts for non-night-owls, anything before `earliest_start`.
   - `novelty`: from the log: "wouldn't go back" (0.1), skipped before (0.3), loved it (0.9), new (1.0).
   - custom criteria: positive/negative signal words.
3. **Adjustments:** +0.5 recurring (if `prefer_recurring`), +0.3 free (if `free_bonus`), plus the profile's own.
4. **Caps.**
5. **Verdict:** `top` ≥ top_threshold, `pick` ≥ pick_threshold, `maybe` within 1.5 below, otherwise `skip`.

The result names the interest it matched (`interest`), which decides its digest section.

## Your judgement (the fit score)
The rule score can't read a lineup or a vibe. Adjust it using:
- **Their rules of thumb** (`goals.operating_rules`): e.g. "recurring beats exceptional" or "go alone" means small, regular, solo-friendly rooms beat a big one-off.
- **The specific ask:** "something chill" or "with my parents" re-weights for this request only; say so.
- **Quality signals you can see:** a headliner they follow, a sold-out warning, a last-minute venue change, terrible reviews of a new promoter.

When your fit score differs from the rule score by 2+ points, say why in a few words. To record it: `lsa log add --events-file <file> --fit-score 8.5 --why '...'`.

## Answering "is this worth it?"
Lead with yes / maybe / skip and one line why, in terms of *their* taste. Then the facts (when, where, price, age, travel time) and anything unverified. If it's a yes, offer to log it as `going`. Never buy or RSVP without an explicit yes.
