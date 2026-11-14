# Testing

```bash
python -m pip install -e ".[dev]"
python -m pytest
```
All tests use an isolated temporary data home and skills folder; they never touch your real `~/.claude` or `~/.local-scene-agent`.

## What's covered
| Area | File | Checks |
|---|---|---|
| Windows & recurring | `tests/test_engine.py` | weekend window from any weekday, custom weekends (Thu–Sun, Sat–Sun), `every`/ordinal/`last` rules, seasonal months, bad rules rejected, annual "coming up" |
| Normalization | `tests/test_engine.py` | price, age and time parsing from listing text |
| Scoring | `tests/test_engine.py` | interest rank ordering, favorite rooms, every hard filter (closed venue, avoid-keyword, hard budget, window, excluded place, age), per-interest exclusions, no-interest cap, unknowns listed not guessed, caps, recurring bonus, late-start penalty, novelty from the log, rule operators |
| Digest | `tests/test_engine.py` | layout order, dedup of the same event from two sources, excluded items absent, `(unverified)` labels, push line ≤ 200 chars, section order follows interest rank, empty-weekend fallback |
| Log | `tests/test_engine.py` | dedup across listings, validated ratings, round-trip to CSV, insights suggesting a weight change |
| Research plan | `tests/test_engine.py` | searches ranked by interest, closed venues skipped, verify list, sources by priority |
| CLI end to end | `tests/test_engine.py` | `digest --save --log` writes the file and log; re-running adds nothing; history logged |
| Onboarding | `tests/onboarding/` | onboarding needed on first run; onboarding skill install; init → blocked approval on skeleton → profile → validate → summary → approve → install; skill holds paths only (no profile contents); edits drop to draft and block digests; second user gets a separate skill; uninstall refuses foreign skills; local and cloud schedule prompts for every task |
| Profile validation | `tests/profile_validation/` | all shipped profiles validate; validator catches removed approvals, duplicate interests, unknown interest refs, bad venue areas, unparseable recurring rules, signal-less custom criteria, approval without timestamp, approval with blocking gaps, bad ids, unknown keys; YAML errors report the line |
| Cross-context | `tests/cross_context/` | six hypothetical users (family, transit-only comedy fan, outdoorsy early riser, student raver, rural retiree, sober maker): each loves one event and never sees another, through the same digest, skill and schedule code with no changes |
| Privacy | `tests/test_no_personal_data.py` | hashed fingerprints of the original user's personal details appear nowhere in the repo |

## What tests can't cover (and how it was checked instead)
- **Live research.** Event sites change daily and many block automated clients, so there's no live-scraping test; the engine doesn't scrape. Research quality depends on the Claude session's tools (fetch, search, browser). The playbooks tell Claude to label unverified items and to say when a tool is missing.
- **Skill invocation inside Claude.** Tests check the generated `SKILL.md` is well-formed with valid frontmatter and filled paths. Invoking it is done by hand: after install, `/local-scene` appears in Claude Code's skill list.
- **Scheduled execution.** Tests render every prompt for both targets. Whether a given scheduled environment has web search, Notion or push is environment-specific; prompts instruct Claude to report missing tools.
