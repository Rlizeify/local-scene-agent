"""Date math: the weekend window, recurring-event rules and annual events.

All times are naive local times in the user's timezone. Claude passes today's
date with --date when it matters (scheduled runs, other timezones).
"""
from __future__ import annotations

import calendar
import datetime as dt
import re

DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
ORDINALS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4,
            "fifth": 5, "5th": 5, "last": -1}


CLOCK_RX = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.I)


def parse_clock(s) -> dt.time | None:
    """First clock time in a free-text string: '18:00' -> 18:00, '6-9pm' -> 18:00, '7am' -> 07:00, 'evening' -> None."""
    if not s:
        return None
    text = str(s).strip().lower()
    m = CLOCK_RX.match(text)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    ampm = m.group(3)
    if not ampm:  # '6-9pm': borrow the meridiem from the end of a range
        tail = re.search(r"(am|pm)\b", text)
        ampm = tail.group(1) if tail and not m.group(2) else None
    if ampm == "pm" and h < 12:
        h += 12
    if ampm == "am" and h == 12:
        h = 0
    if h > 23 or mi > 59:
        return None
    return dt.time(h, mi)


def latest_start(prof: dict) -> dt.time | None:
    return parse_clock(prof.get("weekend", {}).get("latest_start"))


def blocked_by_anchor(prof: dict, start: dt.datetime) -> dict | None:
    """The standing plan whose blocked time covers this start, if any."""
    for a in prof.get("anchors", []):
        if not a.get("blocks") or not a.get("day") or DAYS.index(a["day"]) != start.weekday():
            continue
        lo, hi = parse_clock(a.get("start")), parse_clock(a.get("end"))
        if lo and hi and lo <= start.time() < hi:
            return a
    return None


def _hm(s: str, default: str) -> dt.time:
    h, m = (s or default).split(":")
    return dt.time(int(h), int(m))


def weekend_window(prof: dict, today: dt.date | None = None) -> tuple[dt.datetime, dt.datetime]:
    """The weekend that contains `today`, or the next one if today is outside it."""
    today = today or dt.date.today()
    wk = prof.get("weekend", {})
    sd = DAYS.index(wk.get("starts", {}).get("day", "friday"))
    ed = DAYS.index(wk.get("ends", {}).get("day", "sunday"))
    st, et = _hm(wk.get("starts", {}).get("time"), "17:00"), _hm(wk.get("ends", {}).get("time"), "23:59")
    span = (ed - sd) % 7
    # the most recent start day on or before today
    back = (today.weekday() - sd) % 7
    start_date = today - dt.timedelta(days=back)
    end_date = start_date + dt.timedelta(days=span)
    if today > end_date:
        start_date += dt.timedelta(days=7)
        end_date += dt.timedelta(days=7)
    return dt.datetime.combine(start_date, st), dt.datetime.combine(end_date, et)


def tonight_window(today: dt.date | None = None, now: dt.time | None = None) -> tuple[dt.datetime, dt.datetime]:
    today = today or dt.date.today()
    start = dt.datetime.combine(today, now or dt.time(17, 0))
    return start, dt.datetime.combine(today + dt.timedelta(days=1), dt.time(4, 0))


def days_window(days: int, today: dt.date | None = None) -> tuple[dt.datetime, dt.datetime]:
    today = today or dt.date.today()
    return dt.datetime.combine(today, dt.time(0, 0)), dt.datetime.combine(today + dt.timedelta(days=days - 1), dt.time(23, 59))


def parse_rule(rule: str) -> tuple[int, int]:
    """'every saturday' -> (0, 5); 'first friday' -> (1, 4); 'last saturday monthly' -> (-1, 5).

    Returns (nth, weekday) where nth 0 means every week.
    """
    words = re.findall(r"[a-z0-9]+", rule.lower())
    words = [w for w in words if w not in {"of", "the", "month", "monthly", "each", "weekly", "night", "nights", "s"}]
    day = next((DAYS.index(w.rstrip("s")) for w in words if w.rstrip("s") in DAYS), None)
    if day is None:
        raise ValueError(f"can't find a weekday in rule '{rule}' (use e.g. 'every saturday' or 'first friday')")
    nth = next((ORDINALS[w] for w in words if w in ORDINALS), None)
    if nth is not None:
        return nth, day
    if "every" in words or any(w.endswith("s") and w[:-1] in DAYS for w in words):
        return 0, day
    raise ValueError(f"rule '{rule}' needs 'every' or an ordinal (first, 2nd, third, last)")


def occurs_on(rule: str, date: dt.date) -> bool:
    nth, day = parse_rule(rule)
    if date.weekday() != day:
        return False
    if nth == 0:
        return True
    if nth == -1:
        return date.day + 7 > calendar.monthrange(date.year, date.month)[1]
    return (date.day - 1) // 7 + 1 == nth


def recurring_in_window(prof: dict, start: dt.datetime, end: dt.datetime) -> list[dict]:
    """Profile recurring events that fall inside the window, with their date."""
    out = []
    d = start.date()
    while d <= end.date():
        for r in prof.get("recurring", []):
            if r.get("months") and d.month not in r["months"]:
                continue
            if occurs_on(r["rule"], d):
                t, cutoff = parse_clock(r.get("time")), latest_start(prof)
                if t and cutoff and t > cutoff:
                    continue  # starts after the user's cutoff
                if t and blocked_by_anchor(prof, dt.datetime.combine(d, t)):
                    continue
                out.append({**r, "date": d.isoformat(), "day": DAYS[d.weekday()]})
        d += dt.timedelta(days=1)
    return out


def anchors_in_window(prof: dict, start: dt.datetime, end: dt.datetime) -> list[dict]:
    out = []
    d = start.date()
    while d <= end.date():
        for a in prof.get("anchors", []):
            if a.get("day") and DAYS.index(a["day"]) == d.weekday():
                out.append({**a, "date": d.isoformat()})
        d += dt.timedelta(days=1)
    undated = [a for a in prof.get("anchors", []) if not a.get("day")]
    return out + undated


def annual_coming_up(prof: dict, today: dt.date, months_ahead: int = 1) -> list[dict]:
    """Annual events in this month or the next `months_ahead` months."""
    wanted = [((today.month - 1 + k) % 12) + 1 for k in range(months_ahead + 1)]
    out = []
    for a in prof.get("annual", []):
        hit = [m for m in wanted if m in a["months"]]
        if hit:
            out.append({**a, "when": "this month" if hit[0] == today.month else calendar.month_name[hit[0]]})
    return out
