"""The same engine, unchanged, serves very different people and places.

Each hypothetical user gets one event they should love and one they should never see.
"""
import datetime as dt

import pytest

from conftest import EXAMPLES, install_example
from localscene_agent import digest, profile, schedule, skillgen, window as W
from localscene_agent.evaluate import evaluate
from localscene_agent.events import normalize

SAT = dt.date(2026, 11, 14)

CASES = {
    "family-austin": (
        {"title": "Saturday storytime and puppet show", "venue": "Thinkery", "city": "Mueller", "start": "2026-11-14T10:00", "free": True},
        {"title": "Late DJ night 21+", "venue": "Club", "city": "Downtown", "start": "2026-11-14T22:00", "price_min": 10},
    ),
    "comedy-chicago-transit": (
        {"title": "Improv showcase", "venue": "The Annoyance", "city": "Lakeview", "start": "2026-11-14T21:00", "price_min": 15},
        {"title": "Comedy open mic", "venue": "Bar", "city": "Naperville Suburbs", "start": "2026-11-14T20:00", "price_min": 0},
    ),
    "outdoors-denver": (
        {"title": "Bouldering comp + climbing film night", "venue": "Movement RiNo", "city": "RiNo", "start": "2026-11-14T13:00", "price_min": 20},
        {"title": "Midnight warehouse rave", "venue": "Warehouse", "city": "Denver", "start": "2026-11-14T23:59", "price_min": 90},
    ),
    "techno-brooklyn-student": (
        {"title": "Hard techno warehouse night", "venue": "Small room", "city": "Bushwick", "start": "2026-11-14T23:00", "price_min": 20},
        {"title": "EDM night with VIP table packages", "venue": "Mega club", "city": "Manhattan", "start": "2026-11-14T22:00", "price_min": 60},
    ),
    "rural-vermont": (
        {"title": "Contra dance with live string band", "venue": "Grange Hall", "city": "Waterbury", "start": "2026-11-14T19:30", "price_min": 10},
        {"title": "Corporate networking breakfast", "venue": "Hotel", "city": "Burlington", "start": "2026-11-14T08:00", "price_min": 0},
    ),
    "sober-seattle-maker": (
        {"title": "Drop-in pottery workshop", "venue": "Community center", "city": "Ballard", "start": "2026-11-14T14:00", "price_min": 25},
        {"title": "Fremont pub crawl", "venue": "Various bars", "city": "Fremont", "start": "2026-11-14T19:00", "price_min": 15},
    ),
}


@pytest.mark.parametrize("name", sorted(CASES))
def test_love_and_never(name):
    prof = profile.load(EXAMPLES / f"{name}.yaml")
    win = W.weekend_window(prof, SAT)
    love, never = CASES[name]
    good = evaluate(normalize(love), prof, win)
    bad = evaluate(normalize(never), prof, win)
    assert good["verdict"] in ("top", "pick"), (name, good)
    assert bad["verdict"] in ("excluded", "skip"), (name, bad)
    assert good["rule_score"] > bad["rule_score"]


@pytest.mark.parametrize("name", sorted(CASES))
def test_same_digest_and_skill_code_path(home, name):
    uid = install_example(name)
    prof = profile.load(EXAMPLES / f"{name}.yaml")
    res = digest.build(list(CASES[name]), prof, SAT)
    assert res["counts"]["top"] >= 1 and len(res["push"]) <= 200
    assert skillgen.install(uid, skill_name=f"local-scene-{uid}").exists()
    assert schedule.render("weekend-digest", uid, "cloud")


def test_rural_long_drive_still_a_pick():
    """'The drive is not a reason': an hour away still makes it for a top interest."""
    prof = profile.load(EXAMPLES / "rural-vermont.yaml")
    r = evaluate(normalize({"title": "Contra dance", "city": "Burlington", "start": "2026-11-14T19:30", "price_min": 12}),
                 prof, W.weekend_window(prof, SAT))
    assert r["minutes"] == 60 and r["verdict"] in ("top", "pick")


def test_family_bedtime_is_soft():
    """Past the kids' bedtime still shows up (maybe grandma's babysitting), just ranked well down and flagged."""
    prof = profile.load(EXAMPLES / "family-austin.yaml")
    win = W.weekend_window(prof, SAT)
    late = evaluate(normalize({"title": "Family day concert in the park", "city": "Zilker", "start": "2026-11-14T19:30"}), prof, win)
    early = evaluate(normalize({"title": "Family day concert in the park", "city": "Zilker", "start": "2026-11-14T10:00"}), prof, win)
    assert late["verdict"] != "excluded" and "bedtime" in late["heads_up"][0]
    assert early["rule_score"] - late["rule_score"] >= 2.5


def test_family_weekend_is_saturday_morning_to_sunday():
    prof = profile.load(EXAMPLES / "family-austin.yaml")
    lo, hi = W.weekend_window(prof, dt.date(2026, 11, 13))  # a Friday
    assert lo == dt.datetime(2026, 11, 14, 8, 0) and hi == dt.datetime(2026, 11, 15, 18, 0)
