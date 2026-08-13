#!/usr/bin/env python3
"""Render data/contributions.json as animated monochrome heatmap SVGs.

Outputs assets/contributions-dark.svg and assets/contributions-light.svg,
styled to match the profile's black/white terminal aesthetic. Cells sweep
in diagonally on load (one-shot, CSS animations — GitHub runs these inside
<img>-loaded SVGs). Stdlib only.

Set STATIC=1 to skip animations (useful for thumbnail previews).
"""

import json
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
STATIC = os.environ.get("STATIC") == "1"

CELL = 12
GAP = 3
STEP = CELL + GAP

PAD_X = 34
LABEL_LEFT = 34
LABEL_TOP = 22
CHROME_H = 42
FOOTER_H = 64

THEMES = {
    "dark": {
        "bg_a": "#0B0B0B",
        "bg_b": "#161616",
        "frame": "#FFFFFF",
        "frame_op": ".14",
        "ink": "#F5F5F5",
        "dim": "#8A8A8A",
        "faint": "#5C5C5C",
        "levels": ["#1C1C1C", "#3D3D3D", "#6E6E6E", "#B3B3B3", "#FFFFFF"],
        "level_stroke": "#FFFFFF",
        "lights": ["#3D3D3D", "#5C5C5C", "#8A8A8A"],
    },
    "light": {
        "bg_a": "#FFFFFF",
        "bg_b": "#F2F2F2",
        "frame": "#111111",
        "frame_op": ".18",
        "ink": "#111111",
        "dim": "#5C5C5C",
        "faint": "#8A8A8A",
        "levels": ["#E8E8E8", "#C4C4C4", "#8F8F8F", "#4A4A4A", "#111111"],
        "level_stroke": "#111111",
        "lights": ["#C4C4C4", "#A3A3A3", "#8F8F8F"],
    },
}

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load_days():
    data = json.loads(DATA.read_text())
    return data["user"], data["days"]


def stats(days):
    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"])
    longest = cur = 0
    for d in days:
        cur = cur + 1 if d["count"] > 0 else 0
        longest = max(longest, cur)
    current = 0
    for d in reversed(days):
        if d["count"] > 0:
            current += 1
        elif current == 0 and d is days[-1]:
            continue  # today may have no contributions yet
        else:
            break
    return total, longest, current, best


def build(theme_name, user, days):
    t = THEMES[theme_name]

    # lay out into week columns, GitHub-style (weeks start Sunday)
    first = date.fromisoformat(days[0]["date"])
    cols = {}
    months_at = {}  # week index -> month label
    prev_month = None
    for d in days:
        dt = date.fromisoformat(d["date"])
        week = ((dt - first).days + first.isoweekday() % 7) // 7
        cols.setdefault(week, []).append((dt, d))
        if dt.month != prev_month:
            if dt.day <= 7 or prev_month is None:
                months_at.setdefault(week, MONTHS[dt.month - 1])
            prev_month = dt.month

    n_weeks = max(cols) + 1
    grid_w = n_weeks * STEP - GAP
    grid_h = 7 * STEP - GAP
    width = PAD_X + LABEL_LEFT + grid_w + PAD_X
    grid_x = PAD_X + LABEL_LEFT
    grid_y = CHROME_H + LABEL_TOP + 10
    height = grid_y + grid_h + FOOTER_H

    total, longest, current, best = stats(days)
    best_dt = date.fromisoformat(best["date"])
    sweep_end = (n_weeks - 1) * 0.018 + 6 * 0.045 + 0.42

    anim_css = "" if STATIC else f"""
    .c    {{ opacity: 0; animation: cell .42s cubic-bezier(.2,.8,.3,1) both; }}
    .fade {{ opacity: 0; animation: fade .5s ease-out both; }}
    .cur  {{ opacity: 0; animation: fade .01s linear {sweep_end + .9:.2f}s forwards,
                       blink 1.1s steps(1) {sweep_end + .9:.2f}s infinite; }}
    @keyframes cell  {{ from {{ opacity: 0; transform: translateY(-6px); }}
                        to   {{ opacity: 1; transform: none; }} }}
    @keyframes fade  {{ from {{ opacity: 0; transform: translateY(4px); }}
                        to   {{ opacity: 1; transform: none; }} }}
    @keyframes blink {{ 0%, 54% {{ opacity: 1; }} 55%, 100% {{ opacity: 0; }} }}
    @media (prefers-reduced-motion: reduce) {{
      * {{ animation-duration: .01s !important; animation-delay: 0s !important;
           animation-iteration-count: 1 !important; }}
    }}"""
    if STATIC:
        anim_css = ".c, .fade, .cur { opacity: 1; }"

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="GitHub contribution heatmap for {user}: {total} contributions in the last year">'
    )
    parts.append(f"""  <style>
    .mono {{ font-family: "JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", Consolas, monospace; }}
    text  {{ font-size: 12px; }}
    .c    {{ transform-box: fill-box; transform-origin: center; }}
    {anim_css}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t['bg_a']}"/>
      <stop offset="1" stop-color="{t['bg_b']}"/>
    </linearGradient>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" fill="url(#bg)"
        stroke="{t['frame']}" stroke-opacity="{t['frame_op']}" stroke-width="1.5"/>""")

    # window chrome
    lx = PAD_X
    for i, c in enumerate(t["lights"]):
        parts.append(f'  <circle cx="{lx + i * 20}" cy="{CHROME_H // 2 + 3}" r="5.5" fill="{c}"/>')
    parts.append(
        f'  <text class="mono" x="{width / 2:.0f}" y="{CHROME_H // 2 + 7}" text-anchor="middle" '
        f'fill="{t["dim"]}" font-size="12.5">~ $ git log --graph · {user}</text>'
    )
    parts.append(
        f'  <line x1="{PAD_X - 10}" y1="{CHROME_H + 4}" x2="{width - PAD_X + 10}" y2="{CHROME_H + 4}" '
        f'stroke="{t["frame"]}" stroke-opacity=".08"/>'
    )

    # month labels
    for week, label in months_at.items():
        parts.append(
            f'  <text class="mono fade" style="animation-delay:{.25 + week * .012:.2f}s" '
            f'x="{grid_x + week * STEP}" y="{grid_y - 12}" fill="{t["faint"]}" font-size="10.5">{label}</text>'
        )

    # weekday labels
    for row, label in [(1, "Mon"), (3, "Wed"), (5, "Fri")]:
        parts.append(
            f'  <text class="mono fade" style="animation-delay:.3s" x="{PAD_X - 4}" '
            f'y="{grid_y + row * STEP + CELL - 2}" fill="{t["faint"]}" font-size="10.5">{label}</text>'
        )

    # cells
    for week in sorted(cols):
        for dt, d in cols[week]:
            row = dt.isoweekday() % 7
            x = grid_x + week * STEP
            y = grid_y + row * STEP
            delay = "" if STATIC else f' style="animation-delay:{week * .018 + row * .045:.3f}s"'
            fill = t["levels"][d["level"]]
            stroke = (
                f' stroke="{t["level_stroke"]}" stroke-opacity=".06"'
                if d["level"] == 0 else ""
            )
            label = f'{d["count"]} on {dt.isoformat()}'
            parts.append(
                f'  <rect class="c"{delay} x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                f'rx="3" fill="{fill}"{stroke}><title>{label}</title></rect>'
            )

    # footer: terminal-style stats + legend
    fy = grid_y + grid_h + 34
    base = sweep_end + 0.15 if not STATIC else 0
    parts.append(
        f'  <text class="mono fade" style="animation-delay:{base:.2f}s" x="{PAD_X}" y="{fy}" fill="{t["ink"]}" font-size="12.5">'
        f'<tspan fill="{t["dim"]}">~ $</tspan> {total:,} contributions'
        f'<tspan fill="{t["faint"]}"> · </tspan><tspan fill="{t["dim"]}">longest</tspan> {longest}d'
        f'<tspan fill="{t["faint"]}"> · </tspan><tspan fill="{t["dim"]}">current</tspan> {current}d'
        f'<tspan fill="{t["faint"]}"> · </tspan><tspan fill="{t["dim"]}">best</tspan> {best["count"]} on {MONTHS[best_dt.month - 1]} {best_dt.day}</text>'
    )
    parts.append(
        f'  <rect class="cur" x="{PAD_X + 8}" y="{fy + 12}" width="7" height="13" fill="{t["ink"]}"/>'
    )

    legend_x = width - PAD_X - 5 * (CELL + 4) - 74
    parts.append(
        f'  <text class="mono fade" style="animation-delay:{base + .1:.2f}s" x="{legend_x - 8}" y="{fy}" '
        f'text-anchor="end" fill="{t["faint"]}" font-size="10.5">less</text>'
    )
    for i, c in enumerate(t["levels"]):
        parts.append(
            f'  <rect class="fade" style="animation-delay:{base + .1 + i * .05:.2f}s" '
            f'x="{legend_x + i * (CELL + 4)}" y="{fy - 10}" width="{CELL}" height="{CELL}" rx="3" fill="{c}"'
            + (f' stroke="{t["level_stroke"]}" stroke-opacity=".06"' if i == 0 else "")
            + "/>"
        )
    parts.append(
        f'  <text class="mono fade" style="animation-delay:{base + .35:.2f}s" '
        f'x="{legend_x + 5 * (CELL + 4) + 6}" y="{fy}" fill="{t["faint"]}" font-size="10.5">more</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    user, days = load_days()
    for theme in THEMES:
        out = ROOT / "assets" / f"contributions-{theme}.svg"
        out.write_text(build(theme, user, days))
        print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
