#!/usr/bin/env python3
"""Fetch the public GitHub contribution calendar for a user (no token needed).

Scrapes https://github.com/users/<user>/contributions and writes
data/contributions.json with one entry per day: {date, count, level}.
Stdlib only — safe to run locally and in CI.
"""

import json
import os
import re
import sys
import urllib.request
from pathlib import Path

USER = os.environ.get("GH_USER", "saransh-100")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "contributions.json"

URL = f"https://github.com/users/{USER}/contributions"

DAY_RE = re.compile(
    r'data-date="(\d{4}-\d{2}-\d{2})"\s+id="([^"]+)"\s+data-level="(\d)"'
)
TIP_RE = re.compile(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>')
COUNT_RE = re.compile(r"^(\d+|No)\b")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "profile-art-bot"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def main() -> int:
    html = fetch(URL)

    counts = {}
    for day_id, text in TIP_RE.findall(html):
        m = COUNT_RE.match(text.strip())
        if m:
            counts[day_id] = 0 if m.group(1) == "No" else int(m.group(1))

    days = []
    for date, day_id, level in DAY_RE.findall(html):
        days.append(
            {"date": date, "count": counts.get(day_id, 0), "level": int(level)}
        )

    if not days:
        print("error: no contribution days parsed — GitHub markup may have changed", file=sys.stderr)
        return 1

    days.sort(key=lambda d: d["date"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"user": USER, "days": days}, indent=2) + "\n")
    total = sum(d["count"] for d in days)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(days)} days, {total} contributions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
