"""Build the research plan for a window: which sources to check, how, and which web searches to run.

The engine doesn't scrape. Event sites change constantly and many block bots, so
Claude does the reading (web fetch, web search or a browser). This module just
makes the plan deterministic and ranked by what the user cares about.
"""
from __future__ import annotations

import datetime as dt

from .profile import ranked_interests


def _dates(lo: dt.datetime, hi: dt.datetime) -> list[dt.date]:
    out, d = [], lo.date()
    while d <= hi.date():
        out.append(d)
        d += dt.timedelta(days=1)
    return out


def plan(prof: dict, lo: dt.datetime, hi: dt.datetime, max_queries: int = 24) -> dict:
    srcs = [s for s in prof["sources"] if s.get("enabled", True)]
    srcs.sort(key=lambda s: (s.get("priority", 2), s["name"]))
    days = _dates(lo, hi)
    month_day = f"{lo:%B} {lo.day}" + (f"-{hi.day}" if hi.month == lo.month and hi.day != lo.day else
                                       f" - {hi:%B} {hi.day}" if hi.date() != lo.date() else "")
    base = prof["home"]["base"]

    queries, seen = [], set()

    def q(s):
        if s.lower() not in seen and len(queries) < max_queries:
            seen.add(s.lower())
            queries.append(s)

    closed_names = [v["name"] for v in prof.get("venues", []) if v.get("status") == "closed"]
    closed = {n.lower() for n in closed_names}
    for i in ranked_interests(prof):
        q(f"{i['label']} events {base} {month_day}")
        for v in i.get("venues", [])[:4]:
            if v.lower() not in closed:
                q(f"{v} {month_day}")
        for a in i.get("artists", [])[:2]:
            q(f"{a} {base} {lo.year}")
    for s in srcs:
        if s.get("access") == "search":
            q(f"{s['name']} {month_day}")

    return {
        "window": [lo.isoformat(timespec="minutes"), hi.isoformat(timespec="minutes")],
        "dates": [d.isoformat() for d in days],
        "knowledge_base": prof.get("knowledge_base", []),
        "sources": [{"name": s["name"], "url": s.get("url"), "access": s.get("access", "fetch"),
                     "priority": s.get("priority", 2), "covers": s.get("covers"), "interests": s.get("interests", [])}
                    for s in srcs],
        "web_searches": queries,
        "skip_venues_marked_closed": sorted(closed_names),
        "verify_before_listing": [v["name"] for v in prof.get("venues", []) if v.get("status") == "verify"],
    }


def plan_markdown(p: dict) -> str:
    out = [f"# Research plan {p['window'][0]} → {p['window'][1]}", ""]
    if p["knowledge_base"]:
        out.append("**Read first (read-only):** " + ", ".join(k.get("title") or k["ref"] for k in p["knowledge_base"]))
        out.append("")
    out.append("## Sources (in priority order)")
    for s in p["sources"]:
        out.append(f"- P{s['priority']} [{s['access']}] {s['name']}" + (f" — {s['url']}" if s.get("url") else "")
                   + (f" ({s['covers']})" if s.get("covers") else ""))
    out += ["", "## Web searches"] + [f"- {q}" for q in p["web_searches"]]
    if p["skip_venues_marked_closed"]:
        out += ["", "Skip (closed): " + ", ".join(p["skip_venues_marked_closed"])]
    if p["verify_before_listing"]:
        out += ["Check still open before listing: " + ", ".join(p["verify_before_listing"])]
    return "\n".join(out) + "\n"
