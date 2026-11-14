"""`lsa`: the Local Scene Agent command line. Claude skills call this; people can too."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

from . import __version__, paths


def _out(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def _load_profile(user: str, require_approved: bool = False) -> dict:
    from . import profile as P
    path = paths.profile_path(user)
    if not path.exists():
        raise SystemExit(f"No profile at {path}. Run onboarding first.")
    try:
        prof = P.load(path)
    except ValueError as e:
        raise SystemExit(str(e))
    if require_approved and prof.get("profile_status") != "approved":
        raise SystemExit("Profile is still a draft. Finish onboarding and run `lsa profile approve` first.")
    return prof


def _log(user: str):
    from .log import EventLog
    return EventLog(paths.log_path(user))


def _today(args) -> dt.date:
    return dt.date.fromisoformat(args.date) if getattr(args, "date", None) else dt.date.today()


def _window(args, prof):
    from . import window as W
    today = _today(args)
    if getattr(args, "tonight", False):
        return W.tonight_window(today)
    if getattr(args, "days", None):
        return W.days_window(args.days, today)
    return W.weekend_window(prof, today)


def _read_events(path: str) -> list[dict]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    data = json.loads(raw)
    return data if isinstance(data, list) else [data]


def _add_window_args(p):
    p.add_argument("--date", help="Treat this date (YYYY-MM-DD) as today")
    p.add_argument("--tonight", action="store_true", help="Tonight only (5pm to 4am)")
    p.add_argument("--days", type=int, help="The next N days instead of the weekend")


# ---------------- commands ----------------

def cmd_status(args):
    from . import profile as P, skillgen
    users = paths.list_users()
    info = {"engine_version": __version__, "engine_root": str(paths.ENGINE_ROOT), "data_home": str(paths.data_home()),
            "users": [], "onboarding_required": not users}
    skills = skillgen.installed_skills()
    for u in users:
        prof = P.load(paths.profile_path(u))
        info["users"].append({
            "id": u, "name": prof["user"]["name"], "profile_status": prof.get("profile_status"),
            "validation_errors": P.validate(prof),
            "blocking_gaps": [g["field"] for g in prof.get("gaps", []) if g.get("blocking")],
            "skills": [s["skill_name"] for s in skills if s.get("user_id") == u],
        })
    info["onboarding_skill_installed"] = any(s.get("kind") == "onboarding" for s in skills)
    _out(info)


def cmd_init(args):
    from . import profile as P
    if not args.user:
        raise SystemExit("Pass --user <id> (a short lowercase id, e.g. a first name).")
    path = paths.profile_path(args.user)
    if path.exists() and not args.force:
        raise SystemExit(f"{path} already exists. Use `lsa profile ...` to update it, or --force to start over.")
    P.save(P.new_skeleton(args.user, args.name), path)
    for sub in ("digests", "documents"):
        (path.parent / sub).mkdir(parents=True, exist_ok=True)
    print(f"Created draft profile: {path}")


def cmd_profile(args):
    from . import profile as P
    user = paths.resolve_user(args.user)
    path = paths.profile_path(user)
    if args.action == "path":
        print(path); return
    if args.action == "approve":
        try:
            P.approve(path)
        except ValueError as e:
            raise SystemExit(str(e))
        print(f"Approved {path}"); return
    if args.action == "touch":
        P.mark_changed(path, args.change or "Profile edited")
        print("Recorded change; profile is back to draft until re-approved."); return
    try:
        prof = P.load(path)
    except ValueError as e:
        if args.action == "validate":
            _out({"valid": False, "errors": [str(e)]})
            sys.exit(1)
        raise SystemExit(str(e))
    if args.action == "validate":
        errs = P.validate(prof)
        _out({"valid": not errs, "errors": errs})
        if errs:
            sys.exit(1)
    elif args.action == "show":
        _out(prof)
    elif args.action == "summary":
        print(P.summary_markdown(prof))


def cmd_window(args):
    from . import window as W
    user = paths.resolve_user(args.user)
    prof = _load_profile(user)
    lo, hi = _window(args, prof)
    _out({"start": lo.isoformat(timespec="minutes"), "end": hi.isoformat(timespec="minutes"),
          "anchors": W.anchors_in_window(prof, lo, hi), "recurring": W.recurring_in_window(prof, lo, hi),
          "coming_up": W.annual_coming_up(prof, _today(args))})


def cmd_recurring(args):
    from . import window as W
    user = paths.resolve_user(args.user)
    prof = _load_profile(user)
    lo, hi = _window(args, prof)
    _out(W.recurring_in_window(prof, lo, hi))


def cmd_plan(args):
    from .research import plan, plan_markdown
    user = paths.resolve_user(args.user)
    prof = _load_profile(user, require_approved=True)
    lo, hi = _window(args, prof)
    p = plan(prof, lo, hi, args.max_queries)
    if args.json:
        _out(p)
    else:
        print(plan_markdown(p))


def cmd_evaluate(args):
    from .evaluate import evaluate
    from .events import normalize
    user = paths.resolve_user(args.user)
    prof = _load_profile(user)
    win = None if args.no_window else _window(args, prof)
    hist = _log(user).rows
    results = [evaluate(normalize(e), prof, win, hist) for e in _read_events(args.events_file)]
    _out(results if len(results) > 1 else results[0])


def cmd_digest(args):
    from . import digest
    from .events import normalize
    from .log import log_history
    user = paths.resolve_user(args.user)
    prof = _load_profile(user, require_approved=True)
    win = _window(args, prof)
    log = _log(user)
    raw = _read_events(args.events_file) if args.events_file else []
    res = digest.build(raw, prof, _today(args), win, log.rows, args.source, args.title)
    logged = 0
    if args.log:
        keep = {r["id"]: r for r in res["scored"] if r["verdict"] in ("top", "pick")}
        for e in raw:
            n = normalize(e)
            if n["id"] in keep:
                _, created = log.add(n, keep.pop(n["id"]), "suggested")
                logged += created
        if logged:
            log.save()
    saved = None
    if args.save:
        kind = "tonight" if args.tonight else f"{args.days}d" if args.days else "weekend"
        saved = paths.user_dir(user) / "digests" / f"{_today(args).isoformat()}-{kind}.md"
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_text(res["markdown"] + f"\n<!-- push: {res['push']} -->\n", encoding="utf-8")
    log_history(paths.history_path(user), {"event": "digest", "window": res["window"], **res["counts"],
                                           "logged": logged, "file": str(saved) if saved else None})
    if args.json:
        _out({k: v for k, v in res.items() if k != "scored" or args.verbose} | {"saved": str(saved) if saved else None,
                                                                                  "logged": logged})
    else:
        print(res["markdown"])
        print(f"PUSH: {res['push']}")
        print(f"COUNTS: {json.dumps(res['counts'])}; logged {logged}" + (f"; saved {saved}" if saved else ""))


def cmd_log(args):
    from .events import normalize
    user = paths.resolve_user(args.user)
    prof = _load_profile(user)
    log = _log(user)
    if args.action == "add":
        from .evaluate import evaluate
        out = []
        for e in _read_events(args.events_file):
            n = normalize(e)
            row, created = log.add(n, evaluate(n, prof, None, log.rows), args.status or "suggested")
            if args.fit_score is not None:
                row["fit_score"] = str(args.fit_score)
            if args.why:
                row["why"] = args.why
            out.append({"id": row["id"], "created": created, "title": row["title"], "event_date": row["event_date"]})
        log.save()
        _out(out)
    elif args.action == "update":
        fields = {}
        for kv in args.set or []:
            k, _, v = kv.partition("=")
            fields[k] = v
        for k in ("status", "rating", "note", "why", "fit_score", "people_met"):
            v = getattr(args, k, None)
            if v is not None:
                fields[k] = v
        if args.return_ is not None:
            fields["return"] = args.return_
        try:
            row = log.update(args.id, **fields)
        except (KeyError, ValueError) as e:
            raise SystemExit(str(e))
        log.save()
        _out(row)
    elif args.action == "list":
        rows = [r for r in log.rows if not args.status or r.get("status") in args.status]
        if args.json:
            _out(rows)
        elif not rows:
            print("Nothing logged yet." if not args.status else f"Nothing with status {', '.join(args.status)}.")
        else:
            for r in rows:
                print(f"{r['id']}  {r.get('event_date', ''):<10} {r.get('status', ''):<10} "
                      f"{r.get('rating') or '-':>2}  {r['title']} @ {r.get('venue', '')}")


def cmd_insights(args):
    from .log import insights
    user = paths.resolve_user(args.user)
    _out(insights(_log(user), _load_profile(user)))


def cmd_history(args):
    from .log import read_history
    user = paths.resolve_user(args.user)
    _out(read_history(paths.history_path(user), args.limit))


def cmd_skill(args):
    from . import skillgen
    if args.action == "install":
        user = paths.resolve_user(args.user)
        dest = skillgen.install(user, args.name, args.force)
        print(f"Installed skill '{dest.name}' at {dest}\nInvoke it with /{dest.name}")
    elif args.action == "install-onboarding":
        dest = skillgen.install_onboarding()
        print(f"Installed onboarding skill at {dest}\nInvoke it with /{dest.name}")
    elif args.action == "uninstall":
        if not args.name:
            raise SystemExit("--name is required")
        skillgen.uninstall(args.name)
        print(f"Removed {args.name}")
    elif args.action == "list":
        _out(skillgen.installed_skills())
    elif args.action == "render":
        user = paths.resolve_user(args.user)
        print(skillgen.render(user, args.name or skillgen.default_skill_name(user)))


def cmd_schedule(args):
    from .schedule import TASKS, render
    if args.action == "list":
        _out(TASKS); return
    user = paths.resolve_user(args.user)
    print(render(args.task, user, args.target))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lsa", description="Local Scene Agent engine")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--home", help="Data directory (default: $LSA_HOME or ~/.local-scene-agent)")
    p.add_argument("--user", help="User id (default: $LSA_USER or the only user)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status", help="Engine, users, skills, and whether onboarding is needed").set_defaults(fn=cmd_status)

    s = sub.add_parser("init", help="Create a draft profile for a new user")
    s.add_argument("--name", required=True)
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_init)

    s = sub.add_parser("profile", help="validate | show | summary | approve | touch | path")
    s.add_argument("action", choices=["validate", "show", "summary", "approve", "touch", "path"])
    s.add_argument("--change", help="With touch: what changed")
    s.set_defaults(fn=cmd_profile)

    s = sub.add_parser("window", help="The date window plus standing plans, recurring events and what's coming up")
    _add_window_args(s)
    s.set_defaults(fn=cmd_window)

    s = sub.add_parser("recurring", help="Profile recurring events that fall in the window")
    _add_window_args(s)
    s.set_defaults(fn=cmd_recurring)

    s = sub.add_parser("plan", help="Research plan: sources in priority order and web searches for the window")
    _add_window_args(s)
    s.add_argument("--max-queries", type=int, default=24)
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_plan)

    s = sub.add_parser("evaluate", help="Score event JSON (file or - for stdin) against the profile")
    s.add_argument("--events-file", required=True)
    s.add_argument("--no-window", action="store_true", help="Don't exclude events outside the window")
    _add_window_args(s)
    s.set_defaults(fn=cmd_evaluate)

    s = sub.add_parser("digest", help="Build the ranked digest from candidate events")
    s.add_argument("--events-file", help="JSON list of candidate events (or - for stdin)")
    s.add_argument("--source", action="append", help="A source you used (repeatable); listed at the end")
    s.add_argument("--title")
    s.add_argument("--save", action="store_true", help="Write it to digests/")
    s.add_argument("--log", action="store_true", help="Log top/pick events as 'suggested' (dedupes)")
    s.add_argument("--json", action="store_true")
    s.add_argument("--verbose", action="store_true", help="With --json: include every score breakdown")
    _add_window_args(s)
    s.set_defaults(fn=cmd_digest)

    s = sub.add_parser("log", help="add | update | list: suggested, planned and attended events")
    s.add_argument("action", choices=["add", "update", "list"])
    s.add_argument("id", nargs="?")
    s.add_argument("--events-file")
    s.add_argument("--status", nargs="*")
    s.add_argument("--rating")
    s.add_argument("--return", dest="return_", choices=["yes", "no", "maybe"])
    s.add_argument("--people-met", dest="people_met")
    s.add_argument("--note")
    s.add_argument("--why")
    s.add_argument("--fit-score", dest="fit_score", type=float)
    s.add_argument("--set", action="append", help="column=value (repeatable)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_log)

    sub.add_parser("insights", help="What your log says about your taste, with suggested profile changes").set_defaults(fn=cmd_insights)

    s = sub.add_parser("history", help="Recent engine runs")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=cmd_history)

    s = sub.add_parser("skill", help="install | install-onboarding | uninstall | list | render")
    s.add_argument("action", choices=["install", "install-onboarding", "uninstall", "list", "render"])
    s.add_argument("--name")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_skill)

    s = sub.add_parser("schedule", help="render <task> | list: prompts for scheduled tasks")
    s.add_argument("action", choices=["render", "list"])
    s.add_argument("task", nargs="?", default="weekend-digest")
    s.add_argument("--target", choices=["local", "cloud"], default="local")
    s.set_defaults(fn=cmd_schedule)
    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if args.home:
        os.environ["LSA_HOME"] = args.home
    if args.cmd == "log" and args.action == "update" and not args.id:
        raise SystemExit("log update needs an id (see `lsa log list`)")
    if args.cmd == "log" and args.action == "add" and not args.events_file:
        raise SystemExit("log add needs --events-file")
    if args.cmd == "log" and args.action == "update" and args.status:
        args.status = args.status[0]
    if args.cmd == "log" and args.action == "add" and args.status:
        args.status = args.status[0]
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args.fn(args)
