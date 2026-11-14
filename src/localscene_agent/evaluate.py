"""Deterministic, explainable event scoring driven entirely by the user profile.

Pipeline: hard filters -> weighted criteria (each 0..1) -> adjustments -> caps.
Unknown data scores a neutral 0.5 and is listed in `unknowns`. This is the "rule
score"; Claude records its own judgement separately as the fit score.

Each result also names the interest the event matched best, which decides the
digest section it lands in.
"""
from __future__ import annotations

import datetime as dt
import re

from .events import fmt_day, fmt_time, norm_text


def _has(text: str, phrase: str) -> bool:
    p = phrase.lower().strip()
    if not p:
        return False
    if re.fullmatch(r"[a-z0-9 ]+", p):
        return re.search(r"\b" + re.escape(p) + r"\b", text) is not None
    return p in text


def _hits(text: str, phrases) -> list[str]:
    t = (text or "").lower()
    return [p for p in phrases or [] if _has(t, p)]


def _get(ev: dict, field: str):
    if field in ev:
        return ev[field]
    return (ev.get("extra") or {}).get(field)


def rule_matches(rule: dict, ev: dict) -> bool:
    """True when the event meets the rule's condition. Missing data never matches (except op=missing)."""
    val, op, target = _get(ev, rule["field"]), rule["op"], rule.get("value")
    if op == "missing":
        return val in (None, "", [])
    if val in (None, ""):
        return False
    if isinstance(val, list):
        val = " ".join(str(v) for v in val)
    if op in ("contains_any", "not_contains_any"):
        hit = bool(_hits(str(val), target if isinstance(target, list) else [target]))
        return hit if op == "contains_any" else not hit
    if op == "equals":
        return str(val).lower() == str(target).lower()
    if op in ("in", "not_in"):
        inside = str(val).lower() in [str(x).lower() for x in target]
        return inside if op == "in" else not inside
    try:
        v, t = float(val), float(target)
    except (TypeError, ValueError):
        return False
    return {"lt": v < t, "lte": v <= t, "gt": v > t, "gte": v >= t}[op]


def _rule_text(rule: dict) -> str:
    return rule.get("reason") or f"{rule['field']} {rule['op']} {rule.get('value')}"


def _text(ev: dict) -> str:
    return " ".join(str(x) for x in [ev.get("title"), ev.get("venue"), ev.get("description"),
                                      " ".join(ev.get("tags") or [])] if x).lower()


def find_venue(ev: dict, prof: dict) -> dict | None:
    name = norm_text(ev.get("venue"))
    if not name:
        return None
    for v in prof.get("venues", []):
        for n in [v["name"]] + v.get("aliases", []):
            nn = norm_text(n)
            if nn and (nn == name or nn in name or name in nn):
                return v
    return None


def find_area(ev: dict, prof: dict) -> dict | None:
    v = find_venue(ev, prof)
    areas = prof["home"]["areas"]
    if v and v.get("area"):
        for a in areas:
            if a["name"] == v["area"]:
                return a
    where = " ".join(x for x in [ev.get("city"), v.get("city") if v else None, ev.get("venue")] if x).lower()
    if not where:
        return None
    best = None
    for a in areas:
        if any(_has(where, p) for p in a["places"]) and (best is None or a["minutes"] < best["minutes"]):
            best = a
    return best


# ---- interest matching ----

def match_interests(ev: dict, prof: dict) -> list[dict]:
    """Every interest the event touches, strongest first: [{id, label, strength, hits}]."""
    text = _text(ev)
    venue = norm_text(ev.get("venue"))
    out = []
    for i in prof["interests"]:
        if _hits(text, i.get("avoid_keywords")):
            continue
        hits, strength = [], 0.0
        kw = _hits(text, i["keywords"])
        if kw:
            hits += kw[:4]
            strength = max(strength, min(1.0, 0.55 + 0.15 * len(kw)))
        for v in i.get("venues", []):
            nv = norm_text(v)
            if nv and venue and (nv in venue or venue in nv):
                hits.append(f"room: {v}")
                strength = max(strength, 0.85 if not kw else 1.0)
        art = _hits(text, i.get("artists")) + _hits(text, i.get("promoters"))
        if art:
            hits += art[:3]
            strength = 1.0
        if i["id"] in (ev.get("interests") or []):
            strength = max(strength, 0.7)
            hits.append("tagged")
        if strength:
            out.append({"id": i["id"], "label": i["label"], "weight": i["weight"], "strength": round(strength, 2), "hits": hits})
    out.sort(key=lambda m: -(m["strength"] * m["weight"]))
    return out


# ---- built-in criteria: each returns (score 0..1 or None for unknown, explanation) ----

def c_interest(ev, prof, ctx):
    matches = ctx["matches"]
    if not matches:
        return 0.0, "doesn't match anything you're into"
    top = matches[0]
    max_w = max(i["weight"] for i in prof["interests"])
    score = top["strength"] * (0.4 + 0.6 * top["weight"] / max_w)
    return round(score, 2), f"{top['label']} ({', '.join(top['hits'][:3])})"


def c_distance(ev, prof, ctx):
    area = ctx["area"]
    if not area:
        return None, "couldn't place it on your map"
    mins, mx = area["minutes"], prof["home"].get("max_drive_minutes") or 60
    if mins <= 15:
        return 1.0, f"{area['name']}, ~{mins:g} min"
    if mins > mx:
        return 0.0, f"{area['name']}, ~{mins:g} min (past your usual {mx:g})"
    return round(1.0 - 0.8 * (mins - 15) / max(1, mx - 15), 2), f"{area['name']}, ~{mins:g} min"


def c_venue(ev, prof, ctx):
    v = ctx["venue"]
    fav = any(m["hits"] and any(h.startswith("room:") for h in m["hits"]) for m in ctx["matches"])
    if fav:
        return 1.0, "one of your rooms"
    if v and v.get("status", "active") == "active":
        return 0.8, "a place in your directory"
    if v and v.get("status") == "verify":
        return 0.5, "in your directory but marked 'verify' (may have closed or changed)"
    if not ev.get("venue"):
        return None, "venue not stated"
    return None, "new venue to you"


def c_price(ev, prof, ctx):
    b = prof.get("budget", {})
    lo = ev.get("price_min")
    if ev.get("free") or lo == 0:
        return 1.0, "free"
    if lo is None:
        return None, "price not listed"
    comfy = b.get("comfortable_max")
    if comfy is None:
        return 0.7, f"from ${lo:g}"
    if lo <= comfy:
        return round(1.0 - 0.4 * lo / max(comfy, 1), 2), f"from ${lo:g}"
    hard = b.get("hard_max") or comfy * 2
    return round(max(0.0, 0.5 * (hard - lo) / max(hard - comfy, 1)), 2), f"from ${lo:g} (over your comfortable ${comfy:g})"


def c_timing(ev, prof, ctx):
    start = ev.get("_start")
    if not start or not ev.get("_has_time"):
        return None, "time not listed"
    wk = prof.get("weekend", {})
    h = start.hour + start.minute / 60
    if wk.get("earliest_start"):
        eh, em = map(int, wk["earliest_start"].split(":"))
        if h < eh + em / 60:
            return 0.2, f"starts {fmt_time(start)}, earlier than you like"
    if (h >= 22 or h < 5) and not wk.get("late_nights"):
        return 0.3, f"late start ({fmt_time(start)})"
    return 1.0, f"{start:%a} {fmt_time(start)}"


def c_novelty(ev, prof, ctx):
    past = ctx["history"]
    if not past:
        return None, "no history yet"
    title, venue = norm_text(ev.get("title")), norm_text(ev.get("venue"))
    went_venue = [r for r in past if r.get("status") == "went" and venue and norm_text(r.get("venue")) == venue]
    if any(r.get("return") == "no" for r in went_venue):
        return 0.1, "you said you wouldn't go back"
    if any(r.get("status") == "skipped" and norm_text(r.get("title")) == title for r in past):
        return 0.3, "you skipped this before"
    if any(r.get("return") == "yes" for r in went_venue):
        return 0.9, "a place you liked"
    if went_venue:
        return 0.7, "you've been here"
    return 1.0, "somewhere new"


def c_custom(ev, prof, crit, ctx):
    text = _text(ev) + " " + (ev.get("city") or "").lower()
    pos, neg = _hits(text, crit.get("positive_signals")), _hits(text, crit.get("negative_signals"))
    if not pos and not neg:
        return None, "no signals found"
    score = max(0.0, min(1.0, 0.5 + 0.25 * len(pos) - 0.3 * len(neg)))
    bits = ([f"+ {', '.join(pos[:3])}"] if pos else []) + ([f"- {', '.join(neg[:3])}"] if neg else [])
    return score, " ".join(bits)


BUILTINS = {"interest": c_interest, "distance": c_distance, "venue": c_venue, "price": c_price,
            "timing": c_timing, "novelty": c_novelty}


def evaluate(ev: dict, prof: dict, window: tuple[dt.datetime, dt.datetime] | None = None,
             history: list[dict] | None = None) -> dict:
    """Score one normalized event. `window` excludes events outside it; `history` is log rows."""
    ctx = {"matches": match_interests(ev, prof), "venue": find_venue(ev, prof), "area": find_area(ev, prof),
           "history": history or []}
    excluded = []
    where = " ".join(x for x in [ev.get("city"), ev.get("venue"), (ctx["venue"] or {}).get("city")] if x)
    bad_place = _hits(where, prof["home"].get("excluded_places"))
    if bad_place:
        excluded.append(f"in a place you skip ({', '.join(bad_place)})")
    if ctx["venue"] and ctx["venue"].get("status") == "closed":
        excluded.append(f"{ctx['venue']['name']} is marked closed")
    bad_kw = _hits(_text(ev), prof.get("avoid_keywords"))
    if bad_kw:
        excluded.append(f"mentions {', '.join(bad_kw)}")
    cons, bud = prof.get("constraints", {}), prof.get("budget", {})
    age_ok = cons.get("max_age_limit_ok")
    if ev.get("age_limit") and age_ok is not None and ev["age_limit"] > age_ok:
        excluded.append(f"{ev['age_limit']}+ event")
    if bud.get("hard_max") is not None and ev.get("price_min") is not None and ev["price_min"] > bud["hard_max"]:
        excluded.append(f"cheapest ticket ${ev['price_min']:g} is over your ${bud['hard_max']:g} max")
    start = ev.get("_start")
    if window and start:
        day_only = not ev.get("_has_time")
        lo, hi = window
        if (day_only and not (lo.date() <= start.date() <= hi.date())) or (not day_only and not (lo <= start <= hi)):
            excluded.append(f"outside the window ({fmt_day(start)})")
    for rule in prof["evaluation"].get("hard_filters", []):
        if rule_matches(rule, ev):
            excluded.append(_rule_text(rule))

    breakdown, unknowns, total_w, acc = [], [], 0.0, 0.0
    for crit in prof["evaluation"]["criteria"]:
        fn = BUILTINS.get(crit["id"])
        score, why = fn(ev, prof, ctx) if fn else c_custom(ev, prof, crit, ctx)
        label = crit.get("label") or crit["id"]
        w = crit["weight"]
        if score is None:
            unknowns.append(f"{label}: {why}")
        total_w += w
        acc += w * (0.5 if score is None else score)
        breakdown.append({"criterion": label, "weight": w, "score": None if score is None else round(score, 2), "why": why})

    raw = 10 * acc / total_w if total_w else 0.0
    weighted = raw
    notes = []
    if prof.get("goals", {}).get("prefer_recurring") and ev.get("recurring"):
        raw += 0.5
        notes.append("+0.5: recurring (you're building familiarity)")
    if prof.get("budget", {}).get("free_bonus") and (ev.get("free") or ev.get("price_min") == 0):
        raw += 0.3
        notes.append("+0.3: free")
    for adj in prof["evaluation"].get("adjustments", []):
        if rule_matches(adj, ev):
            raw += adj["points"]
            notes.append(f"{adj['points']:+g}: {_rule_text(adj)}")
    if not ctx["matches"] and raw > 4:
        raw = 4.0
        notes.append("capped at 4: matches none of your interests")
    for cap in prof["evaluation"].get("caps", []):
        if rule_matches(cap, ev) and raw > cap["max_score"]:
            raw = cap["max_score"]
            notes.append(f"capped at {cap['max_score']:g}: {_rule_text(cap)}")
    score = float(round(max(0.0, min(10.0, raw)), 1))

    ev_cfg = prof["evaluation"]
    if excluded:
        verdict = "excluded"
    elif score >= ev_cfg.get("top_threshold", 8):
        verdict = "top"
    elif score >= ev_cfg.get("pick_threshold", 6):
        verdict = "pick"
    elif score >= ev_cfg.get("pick_threshold", 6) - 1.5:
        verdict = "maybe"
    else:
        verdict = "skip"
    top = ctx["matches"][0] if ctx["matches"] else None
    return {"id": ev.get("id"), "title": ev.get("title"), "venue": ev.get("venue"), "city": ev.get("city"),
            "start": ev.get("start"), "url": ev.get("url"), "rule_score": score, "weighted_score": round(weighted, 2),
            "verdict": verdict, "excluded_because": excluded, "interest": top["id"] if top else None,
            "interest_label": top["label"] if top else None, "also_matches": [m["id"] for m in ctx["matches"][1:]],
            "area": ctx["area"]["name"] if ctx["area"] else None,
            "minutes": ctx["area"]["minutes"] if ctx["area"] else None,
            "breakdown": breakdown, "adjustments_and_caps": notes, "unknowns": unknowns,
            "verified": bool(ev.get("verified"))}
