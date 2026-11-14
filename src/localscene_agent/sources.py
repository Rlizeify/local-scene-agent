"""Source discovery: how a brand-new user (or a trip) gets fresh, local event sources.

Every city has the same *kinds* of sources even though the names differ: an alt-weekly
calendar, a tourism board, parks and libraries, venue calendars, a college or community
radio station, record stores, a subreddit with a weekend thread, a DIY/house-show list,
genre aggregators that cover many cities, and a couple of local newsletters.

This module turns a place + the user's interests into a categorized search plan. Claude
runs the searches, opens each candidate, keeps only sources with *current, dated*
listings, and proposes them to the user with an access mode and priority. Nothing here
hardcodes a city.
"""
from __future__ import annotations

from .profile import ranked_interests

# (category, why it matters, query templates). {place} and {city} are filled in.
CATEGORIES = [
    ("alt_weekly", "Local alt-weekly or city paper calendar: the broadest single source in most towns",
     ["{place} alt weekly events calendar", "{place} weekly newspaper things to do this weekend"]),
    ("city_guides", "Tourism board and 'things to do' guides: festivals and big annual events",
     ["{place} official events calendar", "visit {city} events this month"]),
    ("public", "Parks, libraries, museums: daytime, free, family and class listings",
     ["{place} parks and recreation events calendar", "{place} public library events", "{place} museum events calendar"]),
    ("radio", "College and community radio stations: they promote small local shows",
     ["{place} community radio station concert calendar", "{place} college radio local shows"]),
    ("diy", "DIY / small-room scene: house shows, all-ages spaces, record-store shows",
     ["{place} DIY shows calendar", "{place} all ages venue", "{place} record store in-store shows"]),
    ("community", "Community threads and newsletters: what locals actually go to",
     ["reddit {city} weekend events thread", "{place} weekend events newsletter"]),
    ("multi_city", "Platforms that cover many cities; check each has real listings for this one",
     ["{city} events Bandsintown", "{city} events DICE", "{city} Resident Advisor events",
      "{city} events Eventbrite", "{city} Meetup groups"]),
]


def discover(prof: dict, place: str | None = None, per_interest: int = 3) -> dict:
    """A categorized search plan for finding sources in `place` (default: the user's home base)."""
    place = place or prof["home"]["base"]
    city = place.split(",")[0].split("/")[0].strip()
    known = {s["name"].lower() for s in prof.get("sources", [])}
    plan = []
    for cat, why, templates in CATEGORIES:
        plan.append({"category": cat, "why": why, "searches": [t.format(place=place, city=city) for t in templates]})
    for i in ranked_interests(prof):
        kws = i["keywords"][:2]
        qs = [f"{place} {i['label']} calendar"] + [f"best small {k} venues {place}" for k in kws]
        if i.get("daytime"):
            qs.append(f"{place} {kws[0]} weekend daytime")
        plan.append({"category": f"interest:{i['id']}", "why": f"Sources specific to {i['label']}",
                     "searches": qs[:per_interest + 1]})
    return {
        "place": place,
        "already_have": len(known),
        "plan": plan,
        "keep_a_source_only_if": [
            "it lists dated events for the next two weeks (not last year's)",
            "it covers this place, not just the nearest big city",
            "it matches at least one of the user's interests, or covers everything locally",
        ],
        "for_each_kept_source_record": ["name", "url", "covers", "interests", "access (fetch/search/browser/app)",
                                        "priority (1 always, 2 usually, 3 if time)", "found_by: discovery"],
    }


def discover_markdown(d: dict) -> str:
    out = [f"# Source discovery: {d['place']}", f"(Profile already has {d['already_have']} sources.)", ""]
    for c in d["plan"]:
        out.append(f"## {c['category']}: {c['why']}")
        out += [f"- {q}" for q in c["searches"]]
        out.append("")
    out.append("Keep a source only if: " + "; ".join(d["keep_a_source_only_if"]) + ".")
    out.append("Record: " + ", ".join(d["for_each_kept_source_record"]) + ".")
    return "\n".join(out) + "\n"
