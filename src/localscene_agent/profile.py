"""Load, validate, create, approve and summarize user profiles."""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import jsonschema
import yaml

from . import paths

REQUIRED_APPROVALS = ["buy_tickets", "rsvp", "contact_person", "share_personal_data",
                      "edit_knowledge_base", "make_commitment"]
BUILTIN_CRITERIA = {"interest", "distance", "venue", "price", "timing", "novelty"}


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            where = f" (line {mark.line + 1}, column {mark.column + 1})" if mark else ""
            raise ValueError(f"{path} is not valid YAML{where}: {getattr(e, 'problem', e)}") from None
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a YAML mapping")
    return data


def save(profile: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".yaml.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        yaml.safe_dump(profile, f, sort_keys=False, allow_unicode=True, width=100)
    tmp.replace(path)


def schema() -> dict:
    with open(paths.SCHEMA_DIR / "user-profile.schema.json", encoding="utf-8") as f:
        return json.load(f)


def validate(profile: dict) -> list[str]:
    """Return a list of problems (empty = valid). Schema errors plus semantic checks."""
    errors = []
    validator = jsonschema.Draft202012Validator(schema())
    for err in sorted(validator.iter_errors(profile), key=lambda e: list(e.path)):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{loc}: {err.message}")
    if errors:
        return errors

    ids = [i["id"] for i in profile["interests"]]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        errors.append(f"interests: duplicate ids {sorted(dupes)}")
    known = set(ids)
    for where, items in (("venues", profile.get("venues", [])), ("sources", profile.get("sources", [])),
                         ("recurring", profile.get("recurring", [])), ("annual", profile.get("annual", []))):
        for it in items:
            for i in it.get("interests", []):
                if i not in known:
                    errors.append(f"{where}: '{it['name']}' references unknown interest '{i}'")

    from .window import parse_rule
    for r in profile.get("recurring", []):
        try:
            parse_rule(r["rule"])
        except ValueError as e:
            errors.append(f"recurring: '{r['name']}': {e}")

    area_names = {a["name"] for a in profile["home"]["areas"]}
    for v in profile.get("venues", []):
        if v.get("area") and v["area"] not in area_names:
            errors.append(f"venues: '{v['name']}' area '{v['area']}' isn't one of home.areas")

    crit = profile["evaluation"]["criteria"]
    if sum(c["weight"] for c in crit) <= 0:
        errors.append("evaluation/criteria: weights must sum to more than 0")
    for c in crit:
        if c["id"] not in BUILTIN_CRITERIA and not (c.get("positive_signals") or c.get("negative_signals")):
            errors.append(f"evaluation/criteria: custom criterion '{c['id']}' needs positive_signals or negative_signals")

    if profile["profile_status"] == "approved":
        blocking = [g for g in profile.get("gaps", []) if g.get("blocking")]
        if blocking:
            errors.append(f"profile is approved but has blocking gaps: {[g['field'] for g in blocking]}")
        if not profile.get("approved_at"):
            errors.append("profile is approved but approved_at is empty")
    return errors


def new_skeleton(user_id: str, name: str) -> dict:
    """A minimal draft profile the onboarding interview fills in."""
    today = dt.date.today().isoformat()
    return {
        "schema_version": 1,
        "profile_status": "draft",
        "approved_at": None,
        "user": {"id": user_id, "name": name},
        "home": {"base": "TBD", "transport": "car", "max_drive_minutes": 45,
                 "areas": [{"name": "Home", "places": ["TBD"], "minutes": 10}], "excluded_places": []},
        "weekend": {"starts": {"day": "friday", "time": "17:00"}, "ends": {"day": "sunday", "time": "23:59"},
                    "late_nights": False},
        "constraints": {"max_age_limit_ok": 21},
        "budget": {"currency": "USD", "comfortable_max": None, "hard_max": None, "free_bonus": True},
        "interests": [{"id": "tbd", "label": "TBD", "weight": 1, "keywords": ["TBD"]}],
        "avoid_keywords": [],
        "venues": [], "sources": [{"name": "TBD"}], "anchors": [], "recurring": [], "annual": [], "fallbacks": [],
        "goals": {"summary": "", "operating_rules": [], "prefer_recurring": False},
        "evaluation": {
            "pick_threshold": 6, "top_threshold": 8,
            "criteria": [{"id": "interest", "weight": 4}, {"id": "distance", "weight": 2}, {"id": "venue", "weight": 1},
                         {"id": "price", "weight": 1}, {"id": "timing", "weight": 1}, {"id": "novelty", "weight": 1}],
            "hard_filters": [], "caps": [], "adjustments": [],
        },
        "digest": {"top_n": 3, "max_lines": 40, "include_anchors": True, "include_recurring": True,
                   "include_fallbacks": True, "include_coming_up": True, "show_travel_times": True,
                   "push_prefix": "Weekend picks:"},
        "knowledge_base": [],
        "permissions": {"may_use_browser": True, "may_read_calendar": False, "require_approval": list(REQUIRED_APPROVALS)},
        "automation": {"schedules": [], "notify": "only_on_picks",
                       "integrations": {"knowledge_base": "none", "email": "none", "calendar": "none",
                                        "push": "none", "browser": "none"}},
        "gaps": [{"field": "interests", "note": "Not collected yet", "blocking": True},
                 {"field": "home", "note": "Not collected yet", "blocking": True},
                 {"field": "sources", "note": "Not collected yet", "blocking": True}],
        "changelog": [{"date": today, "change": "Profile created"}],
    }


def approve(path: Path) -> dict:
    prof = load(path)
    prof["profile_status"] = "approved"
    prof["approved_at"] = dt.datetime.now().isoformat(timespec="seconds")
    errors = validate(prof)
    if errors:
        raise ValueError("Cannot approve; fix these first:\n  " + "\n  ".join(errors))
    prof.setdefault("changelog", []).append({"date": dt.date.today().isoformat(), "change": "Profile approved"})
    save(prof, path)
    return prof


def mark_changed(path: Path, change: str) -> dict:
    """Record an edit. Any edit to an approved profile drops it back to draft until re-approved."""
    prof = load(path)
    prof.setdefault("changelog", []).append({"date": dt.date.today().isoformat(), "change": change})
    if prof.get("profile_status") == "approved":
        prof["profile_status"] = "draft"
        prof["approved_at"] = None
    save(prof, path)
    return prof


def ranked_interests(prof: dict) -> list[dict]:
    return sorted(prof["interests"], key=lambda i: -i["weight"])


def summary_markdown(prof: dict) -> str:
    """Human-readable profile summary the user approves at the end of onboarding."""
    u, home, ev = prof["user"], prof["home"], prof["evaluation"]
    wk, cons, bud = prof.get("weekend", {}), prof.get("constraints", {}), prof.get("budget", {})
    goals, dg, perm, au = prof.get("goals", {}), prof.get("digest", {}), prof["permissions"], prof.get("automation", {})
    out = [f"# Local scene profile: {u.get('preferred_name') or u['name']}",
           f"Status: **{prof['profile_status']}**" + (f" (approved {prof['approved_at']})" if prof.get("approved_at") else ""), ""]

    out += ["## 1. Where you are", f"- Home base: {home['base']} (transport: {home.get('transport', 'car')})"]
    for a in sorted(home["areas"], key=lambda a: a["minutes"]):
        out.append(f"- {a['name']} (~{a['minutes']:g} min): {', '.join(a['places'])}")
    if home.get("max_drive_minutes"):
        out.append(f"- Farthest you'll usually go: {home['max_drive_minutes']:g} min (farther still shows, scored lower)")
    if home.get("excluded_places"):
        out.append(f"- Never suggest: {', '.join(home['excluded_places'])}")
    out.append("")

    out += ["## 2. What you're into (ranked)"]
    total = sum(i["weight"] for i in prof["interests"])
    for n, i in enumerate(ranked_interests(prof), 1):
        line = f"{n}. **{i['label']}** ({i['weight'] / total:.0%}): {', '.join(i['keywords'][:8])}"
        if i.get("venues"):
            line += f". Rooms: {', '.join(i['venues'][:8])}"
        out.append(line)
        if i.get("avoid_keywords"):
            out.append(f"   - but not: {', '.join(i['avoid_keywords'])}")
    if prof.get("avoid_keywords"):
        out.append(f"- Never suggest anything mentioning: {', '.join(prof['avoid_keywords'])}")
    out.append("")

    out += ["## 3. Your rhythm and limits"]
    st, en = wk.get("starts", {}), wk.get("ends", {})
    out.append(f"- \"The weekend\" runs {st.get('day', 'friday').title()} {st.get('time', '17:00')} to "
               f"{en.get('day', 'sunday').title()} {en.get('time', '23:59')}")
    out.append(f"- Late nights (10pm+ starts): {'yes' if wk.get('late_nights') else 'rarely'}"
               + (f"; nothing before {wk['earliest_start']}" if wk.get("earliest_start") else "")
               + (f"; bedtime {wk['bedtime']} (later things rank lower and get a heads-up, never hidden)"
                  if wk.get("bedtime") else ""))
    if wk.get("prefer_daytime"):
        out.append("- Prefers daytime: evening starts score lower")
    if u.get("goes_with"):
        out.append(f"- Usually goes: {u['goes_with']}")
    if cons.get("max_age_limit_ok") is not None:
        out.append(f"- Age limits OK up to: {cons['max_age_limit_ok']}+" if cons["max_age_limit_ok"] else "- All-ages only")
    if cons.get("kid_friendly_only"):
        out.append("- Kid-friendly only")
    if cons.get("alcohol_free_preferred"):
        out.append("- Prefers alcohol-free settings")
    cur = bud.get("currency", "USD")
    if bud.get("comfortable_max") is not None or bud.get("hard_max") is not None:
        out.append(f"- Budget per ticket: comfortable up to {cur} {bud.get('comfortable_max') or '?'}"
                   + (f", never over {cur} {bud['hard_max']}" if bud.get("hard_max") else ""))
    for a in prof.get("anchors", []):
        when = f" {a['start']}-{a['end']}" if a.get("start") and a.get("end") else (f" {a['time']}" if a.get("time") else "")
        out.append(f"- Standing plan: {a['label']}" + (f", {a['day'].title()}" if a.get("day") else "") + when
                   + (f" at {a['where']}" if a.get("where") else "")
                   + (" (clashing events still shown, flagged and ranked a bit lower)" if a.get("start") and a.get("end") else ""))
    out.append("")

    if goals.get("summary") or goals.get("operating_rules"):
        out += ["## 4. Goals and rules of thumb"]
        if goals.get("summary"):
            out.append(goals["summary"])
        out += [f"- {r}" for r in goals.get("operating_rules", [])]
        out.append("")

    out += ["## 5. How picks are scored",
            f"- Pick at {ev.get('pick_threshold', 6)}+/10; top pick at {ev.get('top_threshold', 8)}+/10",
            "- Dealbreakers (auto-skip):"]
    deal = []
    if home.get("excluded_places"):
        deal.append(f"anything in {', '.join(home['excluded_places'])}")
    deal.append("venues marked closed")
    if prof.get("avoid_keywords"):
        deal.append(f"events mentioning {', '.join(prof['avoid_keywords'])}")
    if bud.get("hard_max"):
        deal.append(f"tickets over {cur} {bud['hard_max']}")
    if cons.get("max_age_limit_ok") is not None:
        deal.append(f"age limit above {cons['max_age_limit_ok']}")
    deal.append("outside the weekend window")
    for t in prof.get("avoid_themes", []):
        deal.append(f"theme: {t} (judged by Claude, beyond keywords)")
    deal += [r.get("reason") or f"{r['field']} {r['op']} {r.get('value')}" for r in ev.get("hard_filters", [])]
    out += [f"  - {d}" for d in deal]
    ctotal = sum(c["weight"] for c in ev["criteria"])
    out.append("- What counts, by weight:")
    for c in sorted(ev["criteria"], key=lambda c: -c["weight"]):
        out.append(f"  - {c.get('label') or c['id']}: {c['weight'] / ctotal:.0%}" + (f" ({c['description']})" if c.get("description") else ""))
    for cap in ev.get("caps", []):
        out.append(f"- Cap: max {cap['max_score']} when {cap.get('reason') or cap['field'] + ' ' + cap['op']}")
    for adj in ev.get("adjustments", []):
        out.append(f"- Adjustment: {adj['points']:+} when {adj.get('reason') or adj['field'] + ' ' + adj['op']}")
    if goals.get("prefer_recurring"):
        out.append("- Recurring events get a bump (you're building familiarity)")
    out.append("")

    out += ["## 6. Where to look"]
    for s in sorted(prof["sources"], key=lambda s: s.get("priority", 2)):
        out.append(f"- {s['name']}" + (f" ({s['covers']})" if s.get("covers") else "")
                   + (f" [{s['access']}]" if s.get("access") else "") + ("" if s.get("enabled", True) else " (off)"))
    for k in prof.get("knowledge_base", []):
        out.append(f"- Your guide: {k.get('title') or k['ref']} ({k['type']}, read-only)")
    v = prof.get("venues", [])
    if v:
        closed = [x["name"] for x in v if x.get("status") == "closed"]
        verify = [x["name"] for x in v if x.get("status") == "verify"]
        out.append(f"- Venue directory: {len(v)} places" + (f"; closed: {', '.join(closed)}" if closed else "")
                   + (f"; need re-checking: {', '.join(verify)}" if verify else ""))
    out.append(f"- Recurring events on file: {len(prof.get('recurring', []))}; annual: {len(prof.get('annual', []))}; "
               f"walk-in fallbacks: {len(prof.get('fallbacks', []))}")
    out.append("")

    out += ["## 7. Digest and automation",
            f"- Digest: top {dg.get('top_n', 3)}, then one section per interest; under ~{dg.get('max_lines', 40)} lines"
            + (f"; style: {dg['style']}" if dg.get("style") else "")]
    for sch in au.get("schedules", []):
        out.append(f"- Scheduled: {sch['task']} {sch.get('when', '')} ({sch.get('target', 'local')})"
                   + ("" if sch.get("enabled", True) else " (off)"))
    out.append(f"- Notifications: {au.get('notify', 'only_on_picks').replace('_', ' ')}")
    integ = au.get("integrations", {})
    if integ:
        out.append("- Integrations: " + ", ".join(f"{k}={v}" for k, v in integ.items()))
    out.append(f"- Always asks you first: {', '.join(perm['require_approval'])}")
    out.append("")

    out += ["## 8. Open gaps"]
    gaps = prof.get("gaps", [])
    out += [f"- {'BLOCKING ' if g.get('blocking') else ''}{g['field']}: {g['note']}" for g in gaps] or ["- none"]
    return "\n".join(out) + "\n"
