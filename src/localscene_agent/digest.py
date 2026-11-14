"""Turn scored events into the phone-scannable weekend digest and a one-line push notification.

Layout: Top N -> standing plans -> one section per interest (in the user's ranked
order) -> recurring this weekend -> coming up -> no-plan fallback -> sources.
Claude may edit the wording afterwards; the structure and ranking come from here.
"""
from __future__ import annotations

import datetime as dt

from . import window as W
from .evaluate import evaluate
from .events import event_key, fmt_day, fmt_time, normalize
from .profile import ranked_interests


def _when(e: dict) -> str:
    s = e.get("_start")
    if not s:
        return "Date TBA"
    return f"{s:%a} {fmt_time(s)}" if e.get("_has_time") else f"{s:%a}"


def _price(e: dict) -> str:
    if e.get("free") or e.get("price_min") == 0:
        return "free"
    if e.get("price_min") is not None:
        return f"from ${e['price_min']:g}"
    return e.get("price_text") or "price TBA"


def _line(e: dict, r: dict, prof: dict) -> str:
    where = ", ".join(x for x in [e.get("venue"), e.get("city")] if x) or "venue TBA"
    bits = [_when(e), e["title"], where, _price(e)]
    if e.get("age_limit"):
        bits.append(f"{e['age_limit']}+")
    show_mins = prof.get("digest", {}).get("show_travel_times", True)
    if show_mins and r.get("minutes") is not None and r["minutes"] > 20:
        bits.append(f"~{r['minutes']:g} min")
    if not e.get("verified"):
        bits.append("(unverified)")
    for h in r.get("heads_up", []):
        bits.append(f"heads-up: {h}")
    return " · ".join(bits) + (f" — {e['url']}" if e.get("url") else "")


def score_all(raw_events: list[dict], prof: dict, win, history=None) -> list[tuple[dict, dict]]:
    """Normalize, dedupe (same title+venue+day) and score. Returns (event, evaluation) sorted best first."""
    seen, out = set(), []
    for raw in raw_events:
        e = normalize(raw)
        key = event_key(e["title"], e.get("venue"), e.get("start"))
        if key in seen:
            continue
        seen.add(key)
        out.append((e, evaluate(e, prof, win, history)))
    out.sort(key=lambda p: -p[1]["rule_score"])
    return out


def build(raw_events: list[dict], prof: dict, today: dt.date | None = None, win=None,
          history=None, sources_used: list[str] | None = None, title: str | None = None) -> dict:
    today = today or dt.date.today()
    win = win or W.weekend_window(prof, today)
    dg = prof.get("digest", {})
    scored = score_all(raw_events, prof, win, history)
    kept = [(e, r) for e, r in scored if r["verdict"] in ("top", "pick", "maybe")]
    top_n = dg.get("top_n", 3)
    top = [(e, r) for e, r in kept if r["verdict"] in ("top", "pick")][:top_n]
    top_ids = {e["id"] for e, _ in top}

    lo, hi = win
    head = title or f"Your weekend: {fmt_day(lo)} – {fmt_day(hi)}"
    md = [f"# {head}", ""]
    if top:
        md.append(f"## Top {len(top)}")
        for n, (e, r) in enumerate(top, 1):
            why = r["interest_label"] or "good fit"
            reasons = [b["why"] for b in r["breakdown"] if (b["score"] or 0) >= 0.85 and b["criterion"] != "interest"][:2]
            md.append(f"{n}. {_line(e, r, prof)}")
            md.append(f"   _why: {why}" + (f"; {'; '.join(reasons)}" if reasons else "") + "_")
        md.append("")
    else:
        md += ["_Nothing cleared your bar this weekend._", ""]

    if dg.get("include_anchors", True):
        anchors = W.anchors_in_window(prof, lo, hi)
        if anchors:
            md.append("## Standing plans")
            for a in anchors:
                md.append(f"- {a.get('day', '').title()[:3] + ' ' if a.get('day') else ''}{a.get('time', '')} {a['label']}".replace("  ", " ")
                          + (f" · {a['where']}" if a.get("where") else ""))
            md.append("")

    for i in ranked_interests(prof):
        items = [(e, r) for e, r in kept if r["interest"] == i["id"] and e["id"] not in top_ids]
        if items:
            md.append(f"## {i['label']}")
            md += [f"- {_line(e, r, prof)}" for e, r in items[:6]]
            md.append("")

    if dg.get("include_recurring", True):
        rec = W.recurring_in_window(prof, lo, hi)
        listed = {e["title"].lower() for e, _ in kept}
        rec = [r for r in rec if r["name"].lower() not in listed]
        if rec:
            md.append("## Recurring this weekend")
            for r in rec:
                md.append(f"- {r['day'].title()[:3]}{' ' + r['time'] if r.get('time') else ''} · {r['name']}"
                          + (f" · {r['where']}" if r.get("where") else "") + (f" · {r['price']}" if r.get("price") else "")
                          + "".join(f" · heads-up: {h}" for h in r.get("heads_up", [])))
            md.append("")

    if dg.get("include_coming_up", True):
        up = W.annual_coming_up(prof, today)
        if up:
            md.append("## Coming up")
            md += [f"- {a['name']} ({a['when']})" + (f" · {a['where']}" if a.get("where") else "") for a in up[:4]]
            md.append("")

    if dg.get("include_fallbacks", True) and len(kept) < 3 and prof.get("fallbacks"):
        md.append("## No-plan fallback")
        md += [f"- {f['name']}" + (f" · {f['where']}" if f.get("where") else "") for f in prof["fallbacks"][:3]]
        md.append("")

    if sources_used:
        md += ["Sources: " + ", ".join(sources_used), ""]

    push_names = [f"{e['title'][:40]} ({(e['_start'] or lo):%a})" for e, _ in top]
    prefix = dg.get("push_prefix", "Weekend picks:")
    push = f"{prefix} " + "; ".join(push_names) if push_names else f"{prefix} quiet weekend, check your fallbacks"
    if len(push) > 200:
        push = push[:197].rstrip() + "..."
    return {
        "window": [lo.isoformat(timespec="minutes"), hi.isoformat(timespec="minutes")],
        "markdown": "\n".join(md).rstrip() + "\n",
        "push": push,
        "counts": {"events_in": len(raw_events), "unique": len(scored), "kept": len(kept),
                   "excluded": sum(r["verdict"] == "excluded" for _, r in scored), "top": len(top)},
        "scored": [r for _, r in scored],
    }
