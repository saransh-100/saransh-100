#!/usr/bin/env python3
"""Render assets/neofetch-dark.svg and assets/neofetch-light.svg.

A neofetch-style terminal card (in the spirit of Andrew6rant's profile):
ASCII portrait on the left, dotted key/value system-info on the right, and
live GitHub stats at the bottom. The portrait types in row by row (SMIL clip
reveal, which GitHub runs inside <img>-loaded SVGs) and the info lines fade
in after it — same monochrome light/dark language as the other assets.

Live numbers come from the public GitHub API and the public contribution
calendar (no token needed; GITHUB_TOKEN is used when present). Fetched stats
are cached in data/stats.json so offline runs still render. Requires Pillow.
"""

import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

from fetch_contributions import COUNT_RE, DAY_RE, TIP_RE

USER = os.environ.get("GH_USER", "saransh-100")
STATIC = os.environ.get("STATIC") == "1"
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "portrait-src.jpg"
CACHE = ROOT / "data" / "stats.json"

# ---- layout -----------------------------------------------------------------
ART_COLS = 62
ART_FONT = 9
ART_ADV = ART_FONT * 0.6

TXT_FONT = 14
TXT_LINE = 20
TXT_W = 64            # info column width, in characters
LEFT_W = 34           # left half of a two-pair stats line

PAD = 28
CHROME_H = 44
RAMP = " .`:-=+*c#%@"

THEMES = {
    "dark": {
        "bg_a": "#0B0B0B",
        "bg_b": "#161616",
        "frame": "#FFFFFF",
        "frame_op": ".14",
        "invert": False,
        "inks": ["#4A4A4A", "#9E9E9E", "#FFFFFF"],
        "glow": True,
        "key": "#9E9E9E",
        "val": "#F5F5F5",
        "dots": "#4A4A4A",
        "pre": "#5C5C5C",
        "title": "#FFFFFF",
        "rule": "#5C5C5C",
        "dim": "#8A8A8A",
        "ink": "#F5F5F5",
        "lights": ["#3D3D3D", "#5C5C5C", "#8A8A8A"],
    },
    "light": {
        "bg_a": "#FFFFFF",
        "bg_b": "#F2F2F2",
        "frame": "#111111",
        "frame_op": ".18",
        "invert": True,
        "inks": ["#B8B8B8", "#6E6E6E", "#111111"],
        "glow": False,
        "key": "#6E6E6E",
        "val": "#111111",
        "dots": "#C4C4C4",
        "pre": "#8A8A8A",
        "title": "#111111",
        "rule": "#A3A3A3",
        "dim": "#5C5C5C",
        "ink": "#111111",
        "lights": ["#C4C4C4", "#A3A3A3", "#8F8F8F"],
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---- stats ------------------------------------------------------------------

def _get(url):
    headers = {"User-Agent": "profile-art-bot", "Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def _calendar_total(year=None):
    url = f"https://github.com/users/{USER}/contributions"
    if year:
        url += f"?from={year}-01-01&to={year}-12-31"
    html = _get(url)
    counts = {}
    for day_id, text in TIP_RE.findall(html):
        m = COUNT_RE.match(text.strip())
        if m:
            counts[day_id] = 0 if m.group(1) == "No" else int(m.group(1))
    return sum(counts.get(day_id, 0) for _, day_id, _ in DAY_RE.findall(html))


def fetch_stats():
    user = json.loads(_get(f"https://api.github.com/users/{USER}"))
    repos = json.loads(_get(f"https://api.github.com/users/{USER}/repos?per_page=100"))
    joined = dt.date.fromisoformat(user["created_at"][:10])
    total = sum(_calendar_total(y) for y in range(joined.year, dt.date.today().year + 1))
    return {
        "repos": user["public_repos"],
        "followers": user["followers"],
        "stars": sum(r["stargazers_count"] for r in repos),
        "joined": joined.isoformat(),
        "contrib_total": total,
        "contrib_year": _calendar_total(),
    }


def load_stats():
    try:
        stats = fetch_stats()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(stats, indent=2) + "\n")
        return stats
    except Exception as e:  # offline / rate-limited: fall back to the cache
        if CACHE.exists():
            print(f"warning: stats fetch failed ({e}); using cached data/stats.json")
            return json.loads(CACHE.read_text())
        raise


def uptime(joined_iso):
    joined = dt.date.fromisoformat(joined_iso)
    today = dt.date.today()
    y = today.year - joined.year
    m = today.month - joined.month
    d = today.day - joined.day
    if d < 0:
        m -= 1
        prev = (today.replace(day=1) - dt.timedelta(days=1)).day
        d += prev
    if m < 0:
        y -= 1
        m += 12
    s = lambda n: "" if n == 1 else "s"
    return f"{y} year{s(y)}, {m} month{s(m)}, {d} day{s(d)}"


# ---- portrait ---------------------------------------------------------------

def load_grid():
    """COLS x rows grid of luminance in [0,1]; None where the red bg is masked."""
    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    rows = int(ART_COLS * (h / w) * (ART_ADV / ART_FONT))

    px = img.load()
    mask = Image.new("L", (w, h), 0)
    mpx = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            is_red_bg = r > 90 and r > g * 1.7 and r > b * 1.7
            mpx[x, y] = 0 if is_red_bg else 255

    gray = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    gray = ImageEnhance.Contrast(gray).enhance(1.15)
    gray = gray.resize((ART_COLS, rows), Image.LANCZOS)
    mask = mask.resize((ART_COLS, rows), Image.LANCZOS)

    gpx, mpx = gray.load(), mask.load()
    return [
        [None if mpx[x, y] < 110 else gpx[x, y] / 255.0 for x in range(ART_COLS)]
        for y in range(rows)
    ]


def rows_to_layers(grid, invert):
    out = []
    for row in grid:
        layers = [[], [], []]
        for v in row:
            if v is None:
                for l in layers:
                    l.append(" ")
                continue
            lum = (1.0 - v if invert else v) ** 0.8
            idx = round(lum * (len(RAMP) - 1))
            if not invert:
                idx = max(idx, 1)
            if idx == 0:
                ch, bucket = " ", 0
            else:
                ch = RAMP[idx]
                bucket = 0 if lum < 0.34 else (1 if lum < 0.68 else 2)
            for i, l in enumerate(layers):
                l.append(ch if i == bucket else " ")
        out.append(["".join(l).rstrip() for l in layers])
    return out


# ---- info lines -------------------------------------------------------------

def seg_key(name):
    """Split dotted keys so the separators render dim, like `Stack·Frontend`."""
    segs = []
    for i, part in enumerate(name.split(".")):
        if i:
            segs.append(("pre", "."))
        segs.append(("key", part))
    return segs


def kv(name, value, width=TXT_W):
    used = 2 + len(name) + 1 + len(value) + 2  # ". name:" + " dots " + value
    dots = "." * max(width - used, 1)
    return [("pre", ". ")] + seg_key(name) + [("dots", f": {dots} "), ("val", value)]


def kv2(n1, v1, n2, v2):
    left = kv(n1, v1, LEFT_W)
    lw = sum(len(t) for _, t in left)
    right = kv(n2, v2, TXT_W - lw - 3 + 2)[1:]  # drop the ". " prefix mid-line
    return left + [("dots", " | ")] + right


def title(name):
    pad = "─" * max(TXT_W - len(name) - 1, 1)
    return [("title", name), ("rule", " " + pad)]


def build_lines(stats):
    n = lambda x: f"{x:,}"
    return [
        title(f"{USER.split('-')[0]}@github"),
        kv("OS", "macOS, Linux"),
        kv("Uptime", uptime(stats["joined"])),
        kv("Host", "What Works Global"),
        kv("Kernel", "Full-Stack Web Developer"),
        kv("Education", "University of Canberra"),
        kv("Domains", "government, defence, startup, enterprise"),
        [],
        kv("Stack.Frontend", "React, Next.js, TypeScript, Tailwind, D3"),
        kv("Stack.Backend", "Node.js, Express, Django, GraphQL"),
        kv("Stack.CMS", "Payload CMS, WordPress"),
        kv("Stack.Databases", "MongoDB, PostgreSQL, Firebase"),
        kv("Stack.Cloud", "AWS, Docker, Linux"),
        [],
        kv("Hobbies.Software", "side projects, gaming"),
        kv("Hobbies.Offline", "running, reading"),
        [],
        title("Contact"),
        kv("Portfolio", "saransh.com.au"),
        kv("LinkedIn", "saransh-kharel"),
        [],
        title("GitHub Stats"),
        kv2("Repos", n(stats["repos"]), "Stars", n(stats["stars"])),
        kv2("Contributions", n(stats["contrib_total"]), "Followers", n(stats["followers"])),
        kv("Contributions.LastYear", n(stats["contrib_year"])),
    ]


# ---- svg --------------------------------------------------------------------

def build(theme_name, grid, stats):
    t = THEMES[theme_name]
    layer_rows = rows_to_layers(grid, t["invert"])
    lines = build_lines(stats)

    art_w = ART_COLS * ART_ADV
    art_h = len(layer_rows) * ART_FONT
    txt_x = int(PAD + art_w + 34)
    txt_w = TXT_W * TXT_FONT * 0.62
    width = int(txt_x + txt_w + PAD)
    body_h = max(art_h, len(lines) * TXT_LINE)
    height = int(CHROME_H + 18 + body_h + PAD + 6)
    art_y = CHROME_H + 18 + (body_h - art_h) / 2
    txt_y = CHROME_H + 18 + (body_h - len(lines) * TXT_LINE) / 2

    stagger, dur = 0.04, 0.45
    art_done = len(layer_rows) * stagger + dur

    parts = [
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Neofetch-style terminal card: ASCII portrait of Saransh beside '
        f'system info and live GitHub stats">'
    ]
    parts.append(f"""  <style>
    .mono {{ font-family: "JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", Consolas, monospace; }}
    .art  {{ font-size: {ART_FONT}px; white-space: pre; }}
    .info {{ font-size: {TXT_FONT}px; white-space: pre; {"" if STATIC else "opacity: 0; animation: on .45s ease-out forwards;"} }}
    .cur  {{ {"" if STATIC else "opacity: 0; animation: on .01s linear var(--d) forwards, blink 1.1s steps(1) var(--d) infinite;"} }}
    @keyframes on    {{ to {{ opacity: 1; }} }}
    @keyframes blink {{ 0%, 54% {{ opacity: 1; }} 55%, 100% {{ opacity: 0; }} }}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t['bg_a']}"/>
      <stop offset="1" stop-color="{t['bg_b']}"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="1.6"/>
    </filter>
    <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
      <rect width="4" height="2" fill="{t['frame']}" opacity=".025"/>
    </pattern>
  </defs>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" fill="url(#bg)"
        stroke="{t['frame']}" stroke-opacity="{t['frame_op']}" stroke-width="1.5"/>""")

    for i, c in enumerate(t["lights"]):
        parts.append(f'  <circle cx="{PAD + i * 20}" cy="{CHROME_H // 2 + 2}" r="5.5" fill="{c}"/>')
    parts.append(
        f'  <text class="mono" x="{width / 2:.0f}" y="{CHROME_H // 2 + 6}" text-anchor="middle" '
        f'fill="{t["dim"]}" font-size="12.5">saransh@github: ~/neofetch</text>'
    )
    parts.append(
        f'  <line x1="{PAD - 10}" y1="{CHROME_H + 2}" x2="{width - PAD + 10}" y2="{CHROME_H + 2}" '
        f'stroke="{t["frame"]}" stroke-opacity=".08"/>'
    )

    # portrait, typed in row by row
    for i, layers in enumerate(layer_rows):
        if not any(layers):
            continue
        y = art_y + i * ART_FONT + ART_FONT
        begin = i * stagger
        clip = ""
        if not STATIC:
            parts.append(f"""  <clipPath id="r{i}">
    <rect x="{PAD}" y="{y - ART_FONT:.1f}" width="0" height="{ART_FONT + 2}">
      <animate attributeName="width" from="0" to="{art_w:.0f}" begin="{begin:.3f}s" dur="{dur}s" fill="freeze"/>
    </rect>
  </clipPath>""")
            clip = f' clip-path="url(#r{i})"'
        parts.append(f"  <g{clip}>")
        for layer, ink in zip(layers, t["inks"]):
            if not layer:
                continue
            if ink == t["inks"][2] and t["glow"]:
                parts.append(
                    f'    <text class="mono art" xml:space="preserve" x="{PAD}" y="{y:.1f}" '
                    f'fill="{ink}" filter="url(#glow)" opacity=".9">{esc(layer)}</text>'
                )
            parts.append(
                f'    <text class="mono art" xml:space="preserve" x="{PAD}" y="{y:.1f}" fill="{ink}">{esc(layer)}</text>'
            )
        parts.append("  </g>")

    parts.append(
        f'  <rect x="{PAD - 6}" y="{art_y - 4:.1f}" width="{art_w + 12:.0f}" height="{art_h + 8}" fill="url(#scan)"/>'
    )

    # info column, fading in line by line behind the portrait reveal
    colors = {"key": t["key"], "val": t["val"], "dots": t["dots"], "pre": t["pre"],
              "title": t["title"], "rule": t["rule"]}
    for i, segs in enumerate(lines):
        if not segs:
            continue
        y = txt_y + i * TXT_LINE + TXT_FONT
        delay = 0.25 + i * 0.07
        spans = "".join(
            f'<tspan fill="{colors[cls]}"{" font-weight=\"600\"" if cls == "title" else ""}>{esc(txt)}</tspan>'
            for cls, txt in segs
        )
        parts.append(
            f'  <text class="mono info" style="animation-delay:{delay:.2f}s" '
            f'xml:space="preserve" x="{txt_x}" y="{y:.1f}">{spans}</text>'
        )

    # blinking cursor after the last line
    last_y = txt_y + (len(lines) - 1) * TXT_LINE + TXT_FONT
    last_w = sum(len(txt) for _, txt in lines[-1]) * TXT_FONT * 0.62
    cur_delay = max(art_done, 0.25 + len(lines) * 0.07) + 0.2
    parts.append(
        f'  <rect class="cur" style="--d:{cur_delay:.2f}s" x="{txt_x + last_w + 8:.0f}" '
        f'y="{last_y - TXT_FONT + 2:.1f}" width="8" height="{TXT_FONT}" fill="{t["ink"]}"/>'
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    stats = load_stats()
    grid = load_grid()
    for theme in THEMES:
        out = ROOT / "assets" / f"neofetch-{theme}.svg"
        out.write_text(build(theme, grid, stats))
        print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
