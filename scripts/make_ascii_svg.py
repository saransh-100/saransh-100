#!/usr/bin/env python3
"""Convert assets/portrait-src.jpg into animated ASCII-art SVGs.

Outputs assets/ascii-dark.svg and assets/ascii-light.svg — a terminal window
that "types" the portrait row by row (SMIL clip reveal, which GitHub runs
inside <img>-loaded SVGs). Ink is split into three brightness layers, with a
soft glow on the brightest characters. Requires Pillow.

The source photo has a flat red background; it is masked to blank space so
the subject floats on the terminal background.

Set STATIC=1 to skip animations (useful for thumbnail previews).
"""

import os
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "portrait-src.jpg"
STATIC = os.environ.get("STATIC") == "1"

COLS = 100
RAMP = " .`:-=+*c#%@"  # sparse -> dense

FONT = 10          # px
ADV = FONT * 0.6   # JetBrains Mono advance
LINE = FONT        # line height ~= font size for a tight grid

PAD = 30
CHROME_H = 44
STATUS_H = 46

THEMES = {
    "dark": {
        "bg_a": "#0B0B0B",
        "bg_b": "#161616",
        "frame": "#FFFFFF",
        "frame_op": ".14",
        "invert": False,          # bright pixels -> dense bright ink
        "inks": ["#4A4A4A", "#9E9E9E", "#FFFFFF"],
        "glow": True,
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
        "invert": True,           # dark pixels -> dense dark ink (print style)
        "inks": ["#B8B8B8", "#6E6E6E", "#111111"],
        "glow": False,
        "dim": "#5C5C5C",
        "faint": "#8A8A8A",
        "ink": "#111111",
        "lights": ["#C4C4C4", "#A3A3A3", "#8F8F8F"],
    },
}


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_grid():
    """Return a COLS x rows grid of luminance values in [0,1], or None for
    background (masked-out red) pixels."""
    img = Image.open(SRC).convert("RGB")
    w, h = img.size
    rows = int(COLS * (h / w) * (ADV / LINE))

    # background mask at full resolution, then downsample
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

    gray = gray.resize((COLS, rows), Image.LANCZOS)
    mask = mask.resize((COLS, rows), Image.LANCZOS)

    gpx, mpx = gray.load(), mask.load()
    grid = []
    for y in range(rows):
        row = []
        for x in range(COLS):
            if mpx[x, y] < 110:
                row.append(None)
            else:
                row.append(gpx[x, y] / 255.0)
        grid.append(row)
    return grid


def rows_to_layers(grid, invert):
    """Split each row into 3 strings (dim/mid/bright layers), spaces elsewhere.

    When not inverted (dark theme), subject pixels never fully vanish: the
    darkest ones still get the sparsest ramp char, so the silhouette survives
    on the dark background as faint texture.
    """
    out = []
    for row in grid:
        layers = [[], [], []]
        for v in row:
            if v is None:
                for l in layers:
                    l.append(" ")
                continue
            lum = 1.0 - v if invert else v
            # gamma lift so faint detail survives
            lum = lum ** 0.8
            idx = round(lum * (len(RAMP) - 1))
            if not invert:
                idx = max(idx, 1)
            if idx == 0:
                ch = " "
                bucket = 0
            else:
                ch = RAMP[idx]
                bucket = 0 if lum < 0.34 else (1 if lum < 0.68 else 2)
            for i, l in enumerate(layers):
                l.append(ch if i == bucket else " ")
        out.append(["".join(l).rstrip() for l in layers])
    return out


def build(theme_name, grid):
    t = THEMES[theme_name]
    layer_rows = rows_to_layers(grid, t["invert"])
    n_rows = len(layer_rows)

    art_w = COLS * ADV
    art_h = n_rows * LINE
    width = int(PAD * 2 + art_w)
    height = int(CHROME_H + 14 + art_h + STATUS_H)
    art_x, art_y = PAD, CHROME_H + 14

    stagger, dur = 0.045, 0.5
    done = n_rows * stagger + dur

    parts = []
    parts.append(
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="Animated ASCII art portrait of Saransh, rendered in a terminal window">'
    )
    cur_begin = f"{done + .3:.2f}s"
    parts.append(f"""  <style>
    .mono {{ font-family: "JetBrains Mono", "Fira Code", "SF Mono", "Cascadia Code", Consolas, monospace; }}
    .art  {{ font-size: {FONT}px; white-space: pre; }}
    {"" if STATIC else f'''.cur  {{ opacity: 0; animation: on .01s linear {done + .3:.2f}s forwards, blink 1.1s steps(1) {done + .3:.2f}s infinite; }}
    .status {{ opacity: 0; animation: on .4s ease-out {done:.2f}s forwards; }}
    @keyframes on    {{ to {{ opacity: 1; }} }}
    @keyframes blink {{ 0%, 54% {{ opacity: 1; }} 55%, 100% {{ opacity: 0; }} }}'''}
  </style>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{t['bg_a']}"/>
      <stop offset="1" stop-color="{t['bg_b']}"/>
    </linearGradient>
    <filter id="glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="1.7"/>
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
        f'fill="{t["dim"]}" font-size="12.5">saransh@github: ~/portrait</text>'
    )
    parts.append(
        f'  <line x1="{PAD - 10}" y1="{CHROME_H + 2}" x2="{width - PAD + 10}" y2="{CHROME_H + 2}" '
        f'stroke="{t["frame"]}" stroke-opacity=".08"/>'
    )

    # per-row typing reveal
    for i, layers in enumerate(layer_rows):
        if not any(layers):
            continue
        y = art_y + i * LINE + FONT  # text baseline
        begin = i * stagger
        clip = ""
        if not STATIC:
            parts.append(f"""  <clipPath id="r{i}">
    <rect x="{art_x}" y="{y - FONT}" width="0" height="{LINE + 2}">
      <animate attributeName="width" from="0" to="{art_w:.0f}" begin="{begin:.3f}s" dur="{dur}s" fill="freeze"/>
    </rect>
  </clipPath>""")
            clip = f' clip-path="url(#r{i})"'
        parts.append(f"  <g{clip}>")
        dim, mid, bright = layers
        if dim:
            parts.append(
                f'    <text class="mono art" xml:space="preserve" x="{art_x}" y="{y}" fill="{t["inks"][0]}">{esc(dim)}</text>'
            )
        if mid:
            parts.append(
                f'    <text class="mono art" xml:space="preserve" x="{art_x}" y="{y}" fill="{t["inks"][1]}">{esc(mid)}</text>'
            )
        if bright:
            if t["glow"]:
                parts.append(
                    f'    <text class="mono art" xml:space="preserve" x="{art_x}" y="{y}" fill="{t["inks"][2]}" filter="url(#glow)" opacity=".9">{esc(bright)}</text>'
                )
            parts.append(
                f'    <text class="mono art" xml:space="preserve" x="{art_x}" y="{y}" fill="{t["inks"][2]}">{esc(bright)}</text>'
            )
        parts.append("  </g>")
        if not STATIC:
            # cursor block riding the reveal edge
            parts.append(f"""  <rect x="{art_x}" y="{y - FONT + 1}" width="{ADV:.1f}" height="{FONT}" fill="{t['ink']}" opacity="0">
    <animate attributeName="x" from="{art_x}" to="{art_x + art_w:.0f}" begin="{begin:.3f}s" dur="{dur}s" fill="freeze"/>
    <set attributeName="opacity" to="1" begin="{begin:.3f}s"/>
    <set attributeName="opacity" to="0" begin="{begin + dur:.3f}s"/>
  </rect>""")

    # scanline overlay for a subtle CRT feel
    parts.append(
        f'  <rect x="{art_x - 6}" y="{art_y - 4}" width="{art_w + 12:.0f}" height="{art_h + 8}" fill="url(#scan)"/>'
    )

    # status line
    sy = height - STATUS_H // 2 - 4
    status_cls = "" if STATIC else ' class="status"'
    parts.append(
        f'  <g{status_cls}><text class="mono" x="{PAD}" y="{sy}" fill="{t["ink"]}" font-size="12.5">'
        f'<tspan fill="{t["dim"]}">~ $</tspan> ascii-render me.jpg <tspan fill="{t["faint"]}">--mono --glow=eyes</tspan>'
        f'<tspan fill="{t["dim"]}"> ✓</tspan></text></g>'
    )
    cur_cls = ' class="cur"' if not STATIC else ""
    parts.append(
        f'  <rect{cur_cls} x="{PAD + 320}" y="{sy - 11}" width="7" height="13" fill="{t["ink"]}"/>'
    )

    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    grid = load_grid()
    for theme in THEMES:
        out = ROOT / "assets" / f"ascii-{theme}.svg"
        out.write_text(build(theme, grid))
        print(f"wrote {out.relative_to(ROOT)} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
