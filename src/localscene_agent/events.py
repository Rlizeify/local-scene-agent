"""Normalize event records (from Claude's research, a fixture, or a pasted listing) to event.schema.json."""
from __future__ import annotations

import datetime as dt
import hashlib
import re

PRICE_RX = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
AGE_RX = re.compile(r"\b(18|19|21)\s?\+")


def norm_text(s: str | None) -> str:
    t = re.sub(r"\(.*?\)", " ", (s or "").lower())
    t = re.sub(r"\b(the|presents|live|at|w/|with)\b", " ", t)
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def parse_start(value) -> dt.datetime | None:
    if not value:
        return None
    if isinstance(value, dt.datetime):
        return value
    if isinstance(value, dt.date):
        return dt.datetime.combine(value, dt.time(0, 0))
    s = str(value).strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s[:19] if "T" in s or " " in s else s, fmt)
        except ValueError:
            continue
    return None


def has_time(value) -> bool:
    return bool(value) and bool(re.search(r"[T ]\d{1,2}:\d{2}", str(value)))


def event_key(title: str, venue: str | None, start) -> str:
    d = parse_start(start)
    base = f"{norm_text(title)}|{norm_text(venue)}|{d.date().isoformat() if d else ''}"
    return hashlib.sha1(base.encode()).hexdigest()[:12]


def normalize(raw: dict, source: str | None = None) -> dict:
    e = dict(raw)
    e["title"] = (e.get("title") or e.get("name") or "").strip()
    e.setdefault("venue", "")
    e.setdefault("city", "")
    e["source"] = e.get("source") or source or "manual"
    e["verified"] = bool(e.get("verified"))
    e.setdefault("tags", [])
    e.setdefault("interests", [])
    text = f"{e.get('price_text', '')}"
    if e.get("price_min") is None and e.get("price_max") is None and text:
        nums = [float(n) for n in PRICE_RX.findall(text)]
        if nums:
            e["price_min"], e["price_max"] = min(nums), max(nums)
        if re.search(r"\bfree\b", text, re.I) and not nums:
            e["free"] = True
    if e.get("free") and e.get("price_min") is None:
        e["price_min"] = 0
    if e.get("age_limit") is None:
        m = AGE_RX.search(f"{e.get('title', '')} {e.get('description', '')} {e.get('price_text', '')}")
        if m:
            e["age_limit"] = int(m.group(1))
    start = parse_start(e.get("start"))
    e["_start"] = start
    e["_has_time"] = has_time(e.get("start"))
    if start:
        e["day"] = start.strftime("%A").lower()
        e["start_hour"] = start.hour if e["_has_time"] else None
    e["_end"] = parse_start(e.get("end")) if has_time(e.get("end")) else None
    e["id"] = e.get("id") or event_key(e["title"], e.get("venue"), e.get("start"))
    return e


def public(e: dict) -> dict:
    """Strip internal fields before printing."""
    return {k: v for k, v in e.items() if not k.startswith("_")}


def fmt_time(t: dt.datetime) -> str:
    """'10pm', '9:30pm' (portable; strftime's %-I doesn't work on Windows)."""
    h = t.hour % 12 or 12
    return f"{h}{'' if t.minute == 0 else f':{t.minute:02d}'}{'am' if t.hour < 12 else 'pm'}"


def fmt_day(t: dt.datetime) -> str:
    """'Sat Nov 14'."""
    return f"{t:%a %b} {t.day}"
