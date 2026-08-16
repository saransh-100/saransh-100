#!/usr/bin/env python3
"""Render the project cards as terminal-window SVGs.

One card per project in assets/projects/<slug>-{dark,light}.svg, in the same
monochrome terminal language as the neofetch card: window chrome, mono type,
staggered fade-in and a blinking cursor (CSS animations, which GitHub runs
inside <img>-loaded SVGs). Each card is embedded in the README inside its own
<a>, so every project keeps its link. Stdlib only. Set STATIC=1 to skip
animations.
"""

import os
import textwrap
from pathlib import Path

STATIC = os.environ.get("STATIC") == "1"
ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "assets" / "projects"

W = 440
PAD = 24
CHROME_H = 36
WRAP = 56          # description wrap width, chars
LINK_WRAP = 50     # link-list wrap width, chars
NAME_F, STACK_F, DESC_F, LINK_F = 14, 11, 11.5, 12
LINE_H = 17

PROJECTS = [
    {
        "slug": "unitracker",
        "emoji": "🛰️",
        "stack": "Next.js · Payload CMS · d3.js",
        "desc": "Research & analytics platform with interactive data "
                "visualisation on a headless CMS architecture.",
        "links": ["unitracker.aspi.org.au"],
    },
    {
        "slug": "allyone",
        "emoji": "🔐",
        "stack": "Django · React · PostgreSQL",
        "desc": "A secure, data-centric platform built for structured "
                "workflows and reliability at scale.",
        "links": ["allyone.com.au"],
    },
    {
        "slug": "vmgd",
        "emoji": "🌋",
        "stack": "WordPress · React · GraphQL",
        "desc": "National platform delivering real-time weather warnings and "
                "disaster advisories, built for public accessibility and "
                "rapid updates.",
        "links": ["vmgd.gov.vu"],
    },
    {
        "slug": "creative-builds",
        "emoji": "🎨",
        "stack": "Next.js · Payload · Relume · Webflow",
        "desc": "Content-driven and marketing platforms with custom CMS "
                "pipelines and performance-focused builds.",
        "links": [
            "himayat.com.au", "cogitogroup.net", "securesme.com",
            "training.cogitogroup.net", "x-rd.com.au", "secd3v.com.au",
            "cbrin.com.au", "fivebridges.org.au", "bittn.com.au",
            "recordtime.com.au", "ngamuru.com",
        ],
    },
    {
        "slug": "amc",
        "emoji": "♿",
        "stack": "Accessibility · WCAG · Multilingual",
        "desc": "Enhanced the AMC website through accessibility upgrades, "
                "navigation improvements, multilingual integration, and "
                "front-end refinements — WCAG-focused fixes with improved "
                "screen reader support.",
        "links": ["amc.org.au"],
    },
    {
        "slug": "haast",
        "emoji": "🧩",
        "stack": "Figma Plugin · Marketing Compliance",
        "desc": "A Figma plugin for marketing compliance, bringing automated "
                "brand and regulatory checks directly into the design "
                "workflow.",
        "links": ["haast.io"],
    },
]

THEMES = {
    "dark": {
        "bg_a": "#0B0B0B",
        "bg_b": "#161616",
        "frame": "#FFFFFF",
        "frame_op": ".14",
        "name": "#FFFFFF",
        "stack": "#8A8A8A",
        "desc": "#9E9E9E",
        "link": "#F5F5F5",
        "dim": "#8A8A8A",
        "faint": "#5C5C5C",
        "ink": "#F5F5F5",
        "lights": ["#3D3D3D", "#5C5C5C", "#8A8A8A"],
    },
    "light": {
        "bg_a": "#FFFFFF",
        "bg_b": "#F2F2F2",
        "frame": "#111111",
        "frame_op": ".18",
        "name": "#111111",
        "stack": "#6E6E6E",
        "desc": "#5C5C5C",
        "link": "#111111",
        "dim": "#5C5C5C",
        "faint": "#8A8A8A",
        "ink": "#111111",
        "lights": ["#C4C4C4", "#A3A3A3", "#8F8F8F"],
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap_links(links):
    """Greedy-wrap the domain list into lines of domain tokens."""
    lines, cur = [], []
    for d in links:
        cand = cur + [d]
        if cur and len(" · ".join(cand)) > LINK_WRAP:
            lines.append(cur)
            cur = [d]
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def body_lines(proj):
    return len(textwrap.wrap(proj["desc"], WRAP)) + len(wrap_links(proj["links"]))


def build(theme_name, proj, index, total, body):
    t = THEMES[theme_name]
    desc_lines = textwrap.wrap(proj["desc"], WRAP)
    link_lines = wrap_links(proj["links"])

    name_y = CHROME_H + 30
    stack_y = name_y + 20
    rule_y = stack_y + 12
    desc_y0 = rule_y + 22
    # link block pinned to the bottom of a uniform-height body
    link_y0 = desc_y0 + (body - len(link_lines)) * LINE_H + 8
    height = link_y0 + len(link_lines) * LINE_H + 8

    fades = 2 + len(desc_lines) + len(link_lines)
    cur_delay = 0.15 + fades * 0.09 + 0.25

    parts = [
        f'<svg viewBox="0 0 {W} {height}" width="{W}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{esc(proj["slug"])} — {esc(proj["stack"])}. {esc(proj["desc"])}">'
    ]
    parts.append(f"""  <style>
    .mono {{ font-family: "JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", Consolas, monospace; }}
    .ln  {{ white-space: pre; {"" if STATIC else "opacity: 0; animation: on .4s ease-out forwards;"} }}
    .cur {{ {"" if STATIC else f"opacity: 0; animation: on .01s linear {cur_delay:.2f}s forwards, blink 1.1s steps(1) {cur_delay:.2f}s infinite;"} }}
    @keyframes on    {{ to {{ opacity: 1; }} }}
    @keyframes blink {{ 0%, 54% {{ opacity: 1; }} 55%, 100% {{ opacity: 0; }} }}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t['bg_a']}"/>
      <stop offset="1" stop-color="{t['bg_b']}"/>
    </linearGradient>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="2" fill="{t['frame']}" opacity=".02"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="{W - 2}" height="{height - 2}" rx="12" fill="url(#bg)"
        stroke="{t['frame']}" stroke-opacity="{t['frame_op']}" stroke-width="1.5"/>""")

    for i, c in enumerate(t["lights"]):
        parts.append(f'  <circle cx="{PAD + i * 16}" cy="{CHROME_H // 2 + 2}" r="4.5" fill="{c}"/>')
    parts.append(
        f'  <text class="mono" x="{W / 2:.0f}" y="{CHROME_H // 2 + 6}" text-anchor="middle" '
        f'fill="{t["dim"]}" font-size="10.5">~/projects/{esc(proj["slug"])}</text>'
    )
    parts.append(
        f'  <text class="mono" x="{W - PAD}" y="{CHROME_H // 2 + 6}" text-anchor="end" '
        f'fill="{t["faint"]}" font-size="10.5">[{index}/{total}]</text>'
    )
    parts.append(
        f'  <line x1="{PAD - 10}" y1="{CHROME_H + 2}" x2="{W - PAD + 10}" y2="{CHROME_H + 2}" '
        f'stroke="{t["frame"]}" stroke-opacity=".08"/>'
    )

    fade = 0

    def ln(inner, y, cls="mono ln"):
        nonlocal fade
        style = "" if STATIC else f' style="animation-delay:{0.15 + fade * 0.09:.2f}s"'
        fade += 1
        parts.append(f'  <text class="{cls}"{style} x="{PAD}" y="{y}">{inner}</text>')

    ln(
        f'<tspan fill="{t["faint"]}">~ $ cat </tspan>'
        f'<tspan fill="{t["name"]}" font-size="{NAME_F}" font-weight="600">{proj["emoji"]} {esc(proj["slug"])}</tspan>',
        name_y,
    )
    ln(f'<tspan fill="{t["stack"]}" font-size="{STACK_F}">{esc(proj["stack"])}</tspan>', stack_y)
    parts.append(
        f'  <line x1="{PAD}" y1="{rule_y}" x2="{W - PAD}" y2="{rule_y}" '
        f'stroke="{t["frame"]}" stroke-opacity=".1"/>'
    )
    for i, line in enumerate(desc_lines):
        ln(f'<tspan fill="{t["desc"]}" font-size="{DESC_F}">{esc(line)}</tspan>', desc_y0 + i * LINE_H)

    for i, tokens in enumerate(link_lines):
        prefix = "↗ " if i == 0 else "  "
        spans = [f'<tspan fill="{t["faint"]}" font-size="{LINK_F}">{prefix}</tspan>']
        for j, d in enumerate(tokens):
            if j:
                spans.append(f'<tspan fill="{t["faint"]}" font-size="{LINK_F}"> · </tspan>')
            spans.append(f'<tspan fill="{t["link"]}" font-size="{LINK_F}">{esc(d)}</tspan>')
        ln("".join(spans), link_y0 + i * LINE_H)

    last_tokens = link_lines[-1]
    last_len = 2 + len(" · ".join(last_tokens))
    last_y = link_y0 + (len(link_lines) - 1) * LINE_H
    cur_x = PAD + last_len * LINK_F * 0.62 + 8
    parts.append(
        f'  <rect class="cur" x="{cur_x:.0f}" y="{last_y - LINK_F + 2}" width="7" '
        f'height="{LINK_F}" fill="{t["ink"]}"/>'
    )
    parts.append(f'  <rect x="{PAD - 8}" y="{CHROME_H + 6}" width="{W - 2 * PAD + 16}" '
                 f'height="{height - CHROME_H - 14}" fill="url(#scan)"/>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    body = max(body_lines(p) for p in PROJECTS)
    for i, proj in enumerate(PROJECTS, 1):
        for theme in THEMES:
            out = OUT_DIR / f"{proj['slug']}-{theme}.svg"
            out.write_text(build(theme, proj, i, len(PROJECTS), body))
            print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
