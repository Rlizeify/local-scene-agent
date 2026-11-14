"""Core engine: windows, recurring rules, scoring, dedup, the log, digests and research plans."""
import datetime as dt
import json

import pytest

from conftest import EXAMPLE_PROFILE, install_profile, run_cli
from localscene_agent import digest, paths, profile, window as W
from localscene_agent.evaluate import evaluate, rule_matches
from localscene_agent.events import normalize
from localscene_agent.log import EventLog, insights
from localscene_agent.research import plan

SAT = dt.date(2026, 11, 14)


@pytest.fixture
def maya():
    return profile.load(EXAMPLE_PROFILE)


# ---- windows and recurring rules ----

@pytest.mark.parametrize("today,start,end", [
    ("2026-11-11", "2026-11-13T17:00", "2026-11-15T22:00"),  # Wednesday -> upcoming weekend
    ("2026-11-14", "2026-11-13T17:00", "2026-11-15T22:00"),  # Saturday -> this weekend
    ("2026-11-15", "2026-11-13T17:00", "2026-11-15T22:00"),  # Sunday -> still this weekend
    ("2026-11-16", "2026-11-20T17:00", "2026-11-22T22:00"),  # Monday -> next weekend
])
def test_weekend_window(maya, today, start, end):
    lo, hi = W.weekend_window(maya, dt.date.fromisoformat(today))
    assert lo.isoformat(timespec="minutes") == start and hi.isoformat(timespec="minutes") == end


def test_custom_weekend_thursday_start():
    prof = {"weekend": {"starts": {"day": "thursday", "time": "20:00"}, "ends": {"day": "sunday", "time": "23:59"}}}
    lo, hi = W.weekend_window(prof, dt.date(2026, 11, 12))
    assert lo == dt.datetime(2026, 11, 12, 20, 0) and hi.date() == dt.date(2026, 11, 15)


@pytest.mark.parametrize("rule,date,expected", [
    ("every saturday", "2026-11-14", True),
    ("saturdays", "2026-11-21", True),
    ("first friday", "2026-11-06", True),
    ("first friday", "2026-11-13", False),
    ("1st Friday monthly", "2026-11-06", True),
    ("3rd saturday", "2026-11-21", True),
    ("third saturday of the month", "2026-11-14", False),
    ("last saturday", "2026-11-28", True),
    ("last saturday", "2026-11-21", False),
    ("second sunday", "2026-11-08", True),
])
def test_recurring_rules(rule, date, expected):
    assert W.occurs_on(rule, dt.date.fromisoformat(date)) is expected


@pytest.mark.parametrize("bad", ["monthly", "every weekend", "first of the month"])
def test_bad_rules_rejected(bad):
    with pytest.raises(ValueError):
        W.parse_rule(bad)


def test_recurring_and_anchors_in_window(maya):
    lo, hi = W.weekend_window(maya, dt.date(2026, 11, 6))  # Fri Nov 6 is a first Friday
    names = [r["name"] for r in W.recurring_in_window(maya, lo, hi)]
    assert "First Friday art walk" in names and "Sunday jazz jam" in names
    assert [a["label"] for a in W.anchors_in_window(maya, lo, hi)] == ["Saturday morning run club"]


def test_seasonal_recurring_respects_months(maya):
    maya["recurring"].append({"name": "Summer night market", "rule": "every saturday", "months": [6, 7, 8]})
    lo, hi = W.weekend_window(maya, SAT)
    assert "Summer night market" not in [r["name"] for r in W.recurring_in_window(maya, lo, hi)]


def test_annual_coming_up(maya):
    assert [a["name"] for a in W.annual_coming_up(maya, dt.date(2026, 7, 20))] == ["Zine fest"]
    assert W.annual_coming_up(maya, dt.date(2026, 7, 20))[0]["when"] == "August"


# ---- normalization ----

def test_normalize_parses_price_age_and_time():
    e = normalize({"title": "Late show 21+", "price_text": "$15 adv / $20 door", "start": "2026-11-14T22:30"})
    assert (e["price_min"], e["price_max"], e["age_limit"]) == (15, 20, 21)
    assert e["day"] == "saturday" and e["start_hour"] == 22 and e["_has_time"]
    assert normalize({"title": "x", "price_text": "Free entry"})["free"] is True
    assert normalize({"title": "x", "start": "2026-11-14"})["_has_time"] is False


# ---- scoring ----

def _score(maya, raw, today=SAT, history=None):
    return evaluate(normalize(raw), maya, W.weekend_window(maya, today), history)


def test_favorite_room_and_top_interest_scores_top(maya, fixture_events):
    r = _score(maya, fixture_events[0])
    assert r["verdict"] == "top" and r["interest"] == "jazz" and r["area"] == "Oakland"


def test_interest_rank_orders_scores(maya):
    jazz = _score(maya, {"title": "jazz trio", "venue": "Somewhere", "city": "Oakland", "start": "2026-11-14T20:00"})
    film = _score(maya, {"title": "35mm screening", "venue": "Somewhere", "city": "Oakland", "start": "2026-11-14T20:00"})
    assert jazz["rule_score"] > film["rule_score"]


@pytest.mark.parametrize("idx,reason", [
    (4, "marked closed"), (5, "bottle service"), (6, "over your"), (7, "outside the window")])
def test_hard_filters(maya, fixture_events, idx, reason):
    r = _score(maya, fixture_events[idx])
    assert r["verdict"] == "excluded" and any(reason in x for x in r["excluded_because"])


def test_excluded_place(maya):
    maya["home"]["excluded_places"] = ["Berkeley"]
    r = _score(maya, {"title": "punk show", "venue": "924 Gilman", "start": "2026-11-14T20:00"})
    assert r["verdict"] == "excluded" and "Berkeley" in r["excluded_because"][0]


def test_age_limit_filter(maya):
    maya["constraints"]["max_age_limit_ok"] = 18
    assert _score(maya, {"title": "jazz 21+", "city": "Oakland", "start": "2026-11-14T20:00"})["verdict"] == "excluded"


def test_interest_avoid_keyword_cancels_only_that_interest(maya, fixture_events):
    r = _score(maya, fixture_events[2])  # punk tribute night
    assert r["interest"] is None and r["verdict"] in ("skip", "maybe")
    assert r["rule_score"] <= 4


def test_no_interest_match_never_a_pick(maya, fixture_events):
    r = _score(maya, fixture_events[9])
    assert r["verdict"] not in ("top", "pick") and "matches none" in " ".join(r["adjustments_and_caps"])


def test_unknowns_listed_not_guessed(maya):
    r = _score(maya, {"title": "jazz night", "start": "2026-11-14"})
    text = " ".join(r["unknowns"])
    assert "price not listed" in text and "time not listed" in text


def test_caps_and_recurring_bonus(maya):
    pricey = _score(maya, {"title": "jazz quartet", "venue": "Yoshi's", "city": "Oakland", "start": "2026-11-14T20:00", "price_min": 60})
    assert pricey["rule_score"] <= 7 and any("capped" in n for n in pricey["adjustments_and_caps"])
    rec = _score(maya, {"title": "jazz jam", "city": "Oakland", "start": "2026-11-15T16:00", "recurring": True})
    assert any("recurring" in n for n in rec["adjustments_and_caps"])


def test_late_start_penalized_for_early_birds(maya):
    maya["weekend"]["late_nights"] = False
    r = _score(maya, {"title": "jazz", "venue": "Yoshi's", "city": "Oakland", "start": "2026-11-14T23:00"})
    assert any(b["criterion"] == "timing" and b["score"] == 0.3 for b in r["breakdown"])


def test_novelty_uses_log(maya):
    hist = [{"title": "x", "venue": "Yoshi's", "status": "went", "return": "no"}]
    r = _score(maya, {"title": "jazz", "venue": "Yoshi's", "city": "Oakland", "start": "2026-11-14T20:00"}, history=hist)
    assert any(b["criterion"] == "novelty" and b["score"] == 0.1 for b in r["breakdown"])


def test_rule_ops():
    ev = {"title": "Hard techno", "price_min": 30, "tags": ["techno", "warehouse"]}
    assert rule_matches({"field": "tags", "op": "contains_any", "value": ["warehouse"]}, ev)
    assert rule_matches({"field": "price_min", "op": "gt", "value": 20}, ev)
    assert not rule_matches({"field": "age_limit", "op": "gt", "value": 18}, ev)
    assert rule_matches({"field": "age_limit", "op": "missing"}, ev)


# ---- digest ----

def test_digest_layout_dedup_and_push(maya, fixture_events):
    res = digest.build(fixture_events, maya, SAT)
    md = res["markdown"]
    assert res["counts"]["unique"] == len(fixture_events) - 1  # the duplicate Yoshi's listing collapses
    assert md.index("## Top 3") < md.index("## Standing plans") < md.index("## Recurring this weekend")
    assert "Old Warehouse Bar" not in md and "bottle service" not in md and "Hard bop trio" not in md
    assert md.count("Vocal jazz quartet") + md.count("Vocal Jazz Quartet") == 1
    assert res["push"].startswith("Weekend picks:") and len(res["push"]) <= 200
    assert "(unverified)" in md


def test_digest_sections_follow_interest_rank(maya):
    events = [{"title": f"{kw} thing {n}", "city": "Oakland", "start": "2026-11-14T19:00", "price_min": 5}
              for n, kw in enumerate(["35mm double feature", "flea market", "35mm repertory", "makers market"] * 2)]
    md = digest.build(events, maya, SAT)["markdown"]
    if "## Markets & makers" in md and "## Repertory film" in md:
        assert md.index("## Markets & makers") < md.index("## Repertory film")


def test_empty_weekend_falls_back(maya):
    res = digest.build([], maya, SAT)
    assert "No-plan fallback" in res["markdown"] and "quiet weekend" in res["push"]


# ---- log ----

def test_log_dedup_update_and_insights(home, maya, fixture_events, tmp_path):
    log = EventLog(tmp_path / "log.csv")
    e = normalize(fixture_events[0])
    row, created = log.add(e, evaluate(e, maya))
    _, again = log.add(normalize(fixture_events[10]))  # same event, different listing
    assert created and not again
    log.update(row["id"], status="went", rating="5", **{"return": "yes"}, note="loved it")
    with pytest.raises(ValueError):
        log.update(row["id"], rating="9")
    log.save()
    reloaded = EventLog(tmp_path / "log.csv")
    assert reloaded.get(row["id"])["status"] == "went" and "loved it" in reloaded.get(row["id"])["notes"]
    second = normalize({"title": "jazz jam", "venue": "Yoshi's", "start": "2026-11-21T20:00"})
    r2, _ = reloaded.add(second, evaluate(second, maya))
    reloaded.update(r2["id"], status="went", rating="5")
    assert any("Raise 'jazz'" in s for s in insights(reloaded, maya)["suggested_profile_changes"])


# ---- research plan ----

def test_plan_ranks_by_interest_and_skips_closed(maya):
    p = plan(maya, *W.weekend_window(maya, SAT))
    assert p["web_searches"][0].startswith("Live jazz")
    assert not any("Old Warehouse" in q for q in p["web_searches"])
    assert p["verify_before_listing"] == ["Eli's Mile High Club"]
    assert [s["priority"] for s in p["sources"]] == sorted(s["priority"] for s in p["sources"])


# ---- CLI end to end ----

def test_cli_digest_save_and_log(home, capsys, fixture_events, tmp_path):
    uid = install_profile(EXAMPLE_PROFILE)
    f = tmp_path / "events.json"
    f.write_text(json.dumps(fixture_events))
    run_cli("--user", uid, "digest", "--date", "2026-11-14", "--events-file", str(f), "--save", "--log")
    out = capsys.readouterr().out
    assert "PUSH: Weekend picks:" in out
    assert (paths.user_dir(uid) / "digests" / "2026-11-14-weekend.md").exists()
    rows = EventLog(paths.log_path(uid)).rows
    assert {r["status"] for r in rows} == {"suggested"} and len(rows) == len({r["id"] for r in rows})
    run_cli("--user", uid, "digest", "--date", "2026-11-14", "--events-file", str(f), "--log")
    assert len(EventLog(paths.log_path(uid)).rows) == len(rows)  # re-running adds nothing
    run_cli("--user", uid, "history")
    assert '"event": "digest"' in capsys.readouterr().out


# ---- early birds: bedtime, daytime preference, standing-plan clashes (all soft) ----

@pytest.fixture
def early(maya):
    maya["weekend"].update(bedtime="20:00", prefer_daytime=True, late_nights=False)
    maya["anchors"] = [{"label": "Surfing", "day": "saturday", "start": "07:00", "end": "12:00"}]
    return maya


@pytest.mark.parametrize("text,expected", [
    ("18:00", (18, 0)), ("6-9pm", (18, 0)), ("7am", (7, 0)), ("5-10pm", (17, 0)), ("12pm", (12, 0)),
    ("10:30 pm", (22, 30)), ("evening", None), ("", None)])
def test_parse_clock(text, expected):
    t = W.parse_clock(text)
    assert (t.hour, t.minute) == expected if expected else t is None


def _jazz(start, end=None):
    e = {"title": "jazz trio", "venue": "Yoshi's", "city": "Oakland", "start": start}
    if end:
        e["end"] = end
    return e


def test_late_start_ranks_lower_with_heads_up_never_hidden(early):
    early_show = _score(early, _jazz("2026-11-14T15:00", "2026-11-14T17:00"))
    late_show = _score(early, _jazz("2026-11-14T20:30"))
    assert late_show["verdict"] != "excluded" and not late_show["excluded_because"]
    assert late_show["rule_score"] < early_show["rule_score"]
    assert "past your 8pm bedtime" in late_show["heads_up"][0]


def test_late_ending_gets_half_penalty(early):
    ends_late = _score(early, _jazz("2026-11-14T18:00", "2026-11-14T21:30"))
    starts_late = _score(early, _jazz("2026-11-14T19:30"))
    assert "ends 9:30pm" in ends_late["heads_up"][0]
    assert ends_late["rule_score"] > starts_late["rule_score"]


def test_standing_plan_clash_is_flagged_not_blocked(early):
    clash = _score(early, {"title": "flea market", "city": "Oakland", "start": "2026-11-14T09:00", "free": True})
    after = _score(early, {"title": "flea market", "city": "Oakland", "start": "2026-11-14T13:00", "free": True})
    sunday = _score(early, {"title": "flea market", "city": "Oakland", "start": "2026-11-15T09:00", "free": True})
    assert clash["verdict"] != "excluded" and "during Surfing" in clash["heads_up"][0]
    assert "leave early" in clash["heads_up"][0]
    assert clash["rule_score"] < after["rule_score"] and not after["heads_up"] and not sunday["heads_up"]
    starts_before = _score(early, {"title": "flea market", "city": "Oakland", "start": "2026-11-14T06:00",
                                   "end": "2026-11-14T08:00", "free": True})
    assert "overlaps the start of Surfing" in starts_before["heads_up"][0]


def test_prefer_daytime_ranks_afternoon_over_evening(early):
    day = _score(early, _jazz("2026-11-15T14:00"))
    eve = _score(early, _jazz("2026-11-15T17:15"))
    assert day["rule_score"] > eve["rule_score"]


def test_recurring_keeps_everything_and_flags(early):
    early["recurring"] = [{"name": "Night walk", "rule": "every friday", "time": "8-10pm"},
                          {"name": "Morning market", "rule": "every saturday", "time": "9am"},
                          {"name": "Afternoon jam", "rule": "every sunday", "time": "16:00"},
                          {"name": "Untimed thing", "rule": "every sunday", "time": "evening"}]
    rec = {r["name"]: r for r in W.recurring_in_window(early, *W.weekend_window(early, SAT))}
    assert set(rec) == {"Night walk", "Morning market", "Afternoon jam", "Untimed thing"}
    assert "bedtime" in rec["Night walk"]["heads_up"][0] and "Surfing" in rec["Morning market"]["heads_up"][0]
    assert rec["Afternoon jam"]["heads_up"] == [] and rec["Untimed thing"]["heads_up"] == []


def test_digest_shows_heads_up(early):
    md = digest.build([_jazz("2026-11-14T20:30"), _jazz("2026-11-15T14:00")], early, SAT)["markdown"]
    assert "heads-up: starts 8:30pm" in md


# ---- source discovery ----

def test_source_discovery_is_place_agnostic(maya):
    from localscene_agent.sources import CATEGORIES, discover
    d = discover(maya, "Eugene, OR")
    cats = [c["category"] for c in d["plan"]]
    assert [c for c, *_ in CATEGORIES] == cats[:len(CATEGORIES)]
    assert cats[len(CATEGORIES)] == "interest:jazz"  # interests follow, in rank order
    flat = " ".join(q for c in d["plan"] for q in c["searches"])
    assert "Eugene" in flat and "Temescal" not in flat
    assert "Temescal" in " ".join(q for c in discover(maya)["plan"] for q in c["searches"])
