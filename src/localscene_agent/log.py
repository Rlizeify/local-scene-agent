"""The event log: one CSV per user of everything suggested, planned and attended.

It does three jobs: dedup (don't pitch the same thing twice), field notes
(ratings, "would I go back", people met), and the feedback that `lsa insights`
turns into suggested profile changes. Written atomically, backed up before changes.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

from .events import event_key, norm_text, parse_start

COLUMNS = ["id", "date_added", "event_date", "title", "venue", "city", "interest", "url", "source", "rule_score",
           "fit_score", "why", "verified", "status", "status_date", "rating", "return", "people_met", "notes"]
STATUSES = ["suggested", "interested", "going", "went", "skipped", "missed", "cancelled"]


class EventLog:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.columns = list(COLUMNS)
        self.rows: list[dict] = []
        if self.path.exists():
            with open(self.path, encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                for col in reader.fieldnames or []:
                    if col not in self.columns:
                        self.columns.append(col)
                self.rows = [dict(r) for r in reader]

    def save(self, backup: bool = True) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if backup and self.path.exists():
            bdir = self.path.parent / "backups"
            bdir.mkdir(exist_ok=True)
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            shutil.copy2(self.path, bdir / f"log-{stamp}.csv")
            for old in sorted(bdir.glob("log-*.csv"))[:-20]:  # keep the 20 newest backups
                old.unlink()
        tmp = self.path.with_suffix(".csv.tmp")
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.columns, extrasaction="ignore")
            w.writeheader()
            for r in self.rows:
                w.writerow({c: r.get(c, "") for c in self.columns})
        os.replace(tmp, self.path)

    def find_duplicate(self, ev: dict) -> dict | None:
        key = ev.get("id") or event_key(ev.get("title", ""), ev.get("venue"), ev.get("start"))
        d = parse_start(ev.get("start"))
        day = d.date().isoformat() if d else ""
        tv = (norm_text(ev.get("title")), norm_text(ev.get("venue")))
        for r in self.rows:
            if r.get("id") == key:
                return r
            if day and r.get("event_date") == day and (norm_text(r.get("title")), norm_text(r.get("venue"))) == tv:
                return r
        return None

    def get(self, row_id: str) -> dict:
        for r in self.rows:
            if r["id"] == row_id:
                return r
        raise KeyError(f"No log row with id {row_id}")

    def add(self, ev: dict, evaluation: dict | None = None, status: str = "suggested") -> tuple[dict, bool]:
        """Add an event. Returns (row, created). Never adds duplicates."""
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        dup = self.find_duplicate(ev)
        if dup:
            return dup, False
        today = dt.date.today().isoformat()
        d = parse_start(ev.get("start"))
        row = {c: "" for c in self.columns}
        row.update({
            "id": ev.get("id") or event_key(ev.get("title", ""), ev.get("venue"), ev.get("start")),
            "date_added": today, "event_date": d.date().isoformat() if d else "",
            "title": ev.get("title", ""), "venue": ev.get("venue", ""), "city": ev.get("city", ""),
            "url": ev.get("url", ""), "source": ev.get("source", ""),
            "verified": "yes" if ev.get("verified") else "unverified", "status": status, "status_date": today,
        })
        if evaluation:
            row["rule_score"] = str(evaluation["rule_score"])
            row["interest"] = evaluation.get("interest") or ""
            good = [b["why"] for b in evaluation["breakdown"] if (b["score"] or 0) >= 0.75][:3]
            row["why"] = "; ".join(good)
        self.rows.append(row)
        return row, True

    def update(self, row_id: str, **fields) -> dict:
        row = self.get(row_id)
        if "status" in fields:
            if fields["status"] not in STATUSES:
                raise ValueError(f"status must be one of {STATUSES}")
            fields.setdefault("status_date", dt.date.today().isoformat())
        if "rating" in fields and str(fields["rating"]) not in {"", "1", "2", "3", "4", "5"}:
            raise ValueError("rating must be 1-5")
        if "return" in fields and fields["return"] not in {"", "yes", "no", "maybe"}:
            raise ValueError("return must be yes, no or maybe")
        note = fields.pop("note", None)
        for k, v in fields.items():
            if k not in self.columns:
                raise KeyError(f"Unknown column {k}")
            row[k] = "" if v is None else str(v)
        if note:
            stamp = dt.date.today().isoformat()
            row["notes"] = (row.get("notes", "") + f" | {stamp}: {note}").lstrip(" |")
        return row


def insights(log: EventLog, prof: dict) -> dict:
    """What the log says about taste: per-interest and per-venue outcomes, plus suggested profile tweaks."""
    by_interest = defaultdict(lambda: {"suggested": 0, "went": 0, "skipped": 0, "ratings": []})
    by_venue = defaultdict(lambda: {"went": 0, "ratings": [], "return": []})
    for r in log.rows:
        i = r.get("interest") or "(none)"
        by_interest[i]["suggested"] += 1
        if r.get("status") == "went":
            by_interest[i]["went"] += 1
            if r.get("rating"):
                by_interest[i]["ratings"].append(int(r["rating"]))
            v = by_venue[r.get("venue") or "(unknown)"]
            v["went"] += 1
            if r.get("rating"):
                v["ratings"].append(int(r["rating"]))
            if r.get("return"):
                v["return"].append(r["return"])
        elif r.get("status") == "skipped":
            by_interest[i]["skipped"] += 1

    def avg(xs):
        return round(sum(xs) / len(xs), 1) if xs else None

    suggestions = []
    weights = {i["id"]: i["weight"] for i in prof["interests"]}
    for iid, s in by_interest.items():
        a = avg(s["ratings"])
        if iid in weights and s["went"] >= 2 and a is not None and a >= 4.5:
            suggestions.append(f"Raise '{iid}' weight (went {s['went']}x, avg rating {a})")
        if iid in weights and s["suggested"] >= 4 and s["went"] == 0 and s["skipped"] >= 3:
            suggestions.append(f"Lower '{iid}' weight (suggested {s['suggested']}x, skipped {s['skipped']}x, never went)")
    known = {v["name"].lower() for v in prof.get("venues", [])}
    for name, v in by_venue.items():
        if "no" in v["return"] and name.lower() in known:
            suggestions.append(f"Mark '{name}' as not-for-you in the venue directory (you said you wouldn't return)")
        if v["went"] and name.lower() not in known and name != "(unknown)" and "yes" in v["return"]:
            suggestions.append(f"Add '{name}' to your venue directory (you'd go back)")
    return {
        "interests": {k: {**v, "avg_rating": avg(v["ratings"])} for k, v in by_interest.items()},
        "venues": {k: {"went": v["went"], "avg_rating": avg(v["ratings"]), "return": v["return"]} for k, v in by_venue.items()},
        "suggested_profile_changes": suggestions,
    }


def log_history(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"at": dt.datetime.now().isoformat(timespec="seconds"), **event}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


def read_history(path: Path, limit: int = 20) -> list[dict]:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        lines = [json.loads(l) for l in f if l.strip()]
    return lines[-limit:]
