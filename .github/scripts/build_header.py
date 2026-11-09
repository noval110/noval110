#!/usr/bin/env python3
"""Builds assets/header.svg, the animated profile header.

A topographic map of a mountain (real contour lines from a height field), a dotted hiking
trail climbing to the summit, a light pulse rolling out from the peak, a typed role line
and a scrolling stack ticker. Pure SVG + CSS/SMIL animation, which GitHub plays inside
README images. Fonts are subset and embedded so the text looks the same everywhere.

Usage: python .github/scripts/build_header.py <fonts_dir>
       fonts_dir holds unbounded.woff2, jakarta.woff2 and mono.woff2 (latin, variable)
Requires: pip install fonttools brotli numpy scikit-image
"""
import base64
import io
import math
import sys
from pathlib import Path

import numpy as np
from fontTools import subset
from fontTools.ttLib import TTFont
from skimage import measure

ROOT = Path(__file__).resolve().parents[2]
FONTS = Path(sys.argv[1])
W, H = 1280, 400
CHARS = "".join(chr(c) for c in range(32, 127)) + "—·°′’↗"

BG = "#0a0609"
INK = "#f8f0f5"
PINK = "#f472b6"
DEEP = "#db2777"


def font_b64(name: str) -> str:
    font = TTFont(FONTS / name)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["kern", "liga"]
    sub = subset.Subsetter(opts)
    sub.populate(text=CHARS)
    sub.subset(font)
    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


U, J, M = font_b64("unbounded.woff2"), font_b64("jakarta.woff2"), font_b64("mono.woff2")


def catmull(p: np.ndarray, closed: bool) -> str:
    """Smooth curve through the points (Catmull-Rom -> cubic Béziers), whole-pixel precision."""
    n = len(p)
    out = [f"M{p[0][0]:.0f} {p[0][1]:.0f}"]
    for i in range(n - 1):
        p0 = p[i - 1] if i > 0 else (p[-2] if closed else p[0])
        p1, p2 = p[i], p[i + 1]
        p3 = p[i + 2] if i + 2 < n else (p[1] if closed else p[-1])
        c1, c2 = p1 + (p2 - p0) / 6, p2 - (p3 - p1) / 6
        out.append(f"C{c1[0]:.0f} {c1[1]:.0f} {c2[0]:.0f} {c2[1]:.0f} {p2[0]:.0f} {p2[1]:.0f}")
    return "".join(out)


# ---------------------------------------------------------------- terrain
PX, PY = 1000, 178  # summit
X0, X1, Y0, Y1 = 520, W + 40, -40, H + 40
STEP = 4
gx, gy = np.meshgrid(np.arange(X0, X1, STEP), np.arange(Y0, Y1, STEP))


def bump(cx, cy, sx, sy, h, rot=0.0):
    c, s = math.cos(rot), math.sin(rot)
    dx, dy = gx - cx, gy - cy
    u, v = dx * c + dy * s, -dx * s + dy * c
    return h * np.exp(-((u / sx) ** 2 + (v / sy) ** 2))


rng = np.random.default_rng(11)
z = (
    bump(PX, PY, 190, 130, 1.0, 0.25)
    + bump(1185, 250, 120, 90, 0.55, -0.4)
    + bump(820, 300, 150, 80, 0.42, 0.2)
    + bump(1110, 60, 110, 70, 0.35)
    + bump(PX + 40, PY + 70, 260, 60, 0.18, 0.5)  # a ridge running down to the right
)
# gentle irregularity so the rings don't look like perfect ellipses
for k, amp in ((0.012, 0.05), (0.025, 0.025)):
    ph = rng.uniform(0, math.tau, 3)
    z += amp * (np.sin(gx * k + ph[0]) * np.cos(gy * k * 1.3 + ph[1]) + np.sin((gx + gy) * k * 0.7 + ph[2]))

LEVELS = np.linspace(0.12, 0.98, 15)
paths, contours, highlights = [], [], []
for li, lev in enumerate(LEVELS):
    t = li / (len(LEVELS) - 1)
    major = li % 4 == 0
    for c in measure.find_contours(z, lev):
        pts = np.column_stack([X0 + c[:, 1] * STEP, Y0 + c[:, 0] * STEP])
        length = float(np.hypot(*np.diff(pts, axis=0).T).sum())
        if length < 40:
            continue
        closed = bool(np.allclose(pts[0], pts[-1]))
        p = pts[::3]
        if closed and not np.allclose(p[0], p[-1]):
            p = np.vstack([p, p[:1]])
        if len(p) < 3:
            continue
        d = catmull(p, closed)
        op = 0.16 + 0.34 * t + (0.12 if major else 0)
        sw = 1.4 if major else 0.9
        L = int(length) + 20
        # each contour is defined once and drawn twice: the line itself, and a bright copy
        # that only shows where the pulse from the summit passes
        pid = f"p{len(paths)}"
        paths.append(f'<path id="{pid}" d="{d}"/>')
        contours.append(
            f'<use href="#{pid}" class="c" stroke-width="{sw}" stroke-opacity="{op:.2f}" '
            f'style="stroke-dasharray:{L};stroke-dashoffset:{L};animation-delay:{0.15 + (1 - t) * 0.9:.2f}s"/>'
        )
        highlights.append(f'<use href="#{pid}" stroke-width="{sw + 0.6}"/>')

# hiking trail: from the bottom edge, switchbacks up to the summit
trail_d = catmull(np.array([(700, 420), (742, 372), (812, 352), (850, 318), (822, 286), (880, 262), (938, 250),
                            (918, 222), (962, 206), (PX, PY + 6)], dtype=float), False)

# ---------------------------------------------------------------- typed role line
ROLES = ["React interfaces", "Go backends", "AI-powered tools", "things that ship"]
CW = 12  # JetBrains Mono advance (0.6em) at 20px
PREFIX = "> building "
TX, TY = 64, 268
RX = TX + len(PREFIX) * CW
T = 14.0  # seconds for the whole cycle
slot = 100 / len(ROLES)
TYPE, HOLD, DEL = 0.30, 0.80, 0.93  # fractions of a slot

type_css, masks, role_svg = [], [], []
caret_kf = ["0%{transform:translateX(0)}"]
for i, r in enumerate(ROLES):
    n = len(r)
    a, b, c, d = i * slot, (i + TYPE) * slot, (i + HOLD) * slot, (i + DEL) * slot
    kf = (
        f"0%{{transform:scaleX(0)}}"
        f"{a:.2f}%{{transform:scaleX(0);animation-timing-function:steps({n},end)}}"
        f"{b:.2f}%{{transform:scaleX(1)}}"
        f"{c:.2f}%{{transform:scaleX(1);animation-timing-function:steps({n},end)}}"
        f"{d:.2f}%,100%{{transform:scaleX(0)}}"
    )
    type_css.append(f".t{i}{{transform-box:fill-box;transform-origin:left center;animation:t{i} {T}s linear infinite}}"
                    f"@keyframes t{i}{{{kf}}}")
    masks.append(f'<mask id="m{i}"><rect class="t{i}" x="{RX}" y="{TY - 22}" width="{n * CW}" height="30" fill="#fff"/></mask>')
    role_svg.append(f'<text class="role" x="{RX}" y="{TY}" mask="url(#m{i})">{r}</text>')
    caret_kf += [
        f"{a:.2f}%{{transform:translateX(0);animation-timing-function:steps({n},end)}}",
        f"{b:.2f}%{{transform:translateX({n * CW}px)}}",
        f"{c:.2f}%{{transform:translateX({n * CW}px);animation-timing-function:steps({n},end)}}",
        f"{d:.2f}%{{transform:translateX(0)}}",
    ]
caret_kf.append("100%{transform:translateX(0)}")

# ---------------------------------------------------------------- stack ticker
STACK = "REACT  ·  TYPESCRIPT  ·  GO  ·  POSTGRESQL  ·  SUPABASE  ·  PYTHON  ·  FASTAPI  ·  PYTORCH  ·  DOCKER  ·  TAILWIND  ·  VITE  ·  "
TK_SIZE, TK_LS = 11, 0.3
TK_W = len(STACK) * (0.6 + TK_LS) * TK_SIZE  # monospace: exact width of one copy
BAND = 352

css = f"""
@font-face{{font-family:U;src:url(data:font/woff2;base64,{U}) format('woff2');font-weight:200 900}}
@font-face{{font-family:J;src:url(data:font/woff2;base64,{J}) format('woff2');font-weight:200 800}}
@font-face{{font-family:M;src:url(data:font/woff2;base64,{M}) format('woff2');font-weight:100 800}}
text{{white-space:pre}}
.k{{font:500 12px M;letter-spacing:.3em;fill:{INK};fill-opacity:.55}}
.name{{font:800 56px U;letter-spacing:-1px;fill:{INK}}}
.name2{{font:800 56px U;letter-spacing:-1px}}
.pre{{font:500 20px M;fill:{INK};fill-opacity:.5}}
.role{{font:600 20px M;fill:{PINK}}}
.meta{{font:500 15px J;fill:{INK};fill-opacity:.55}}
.pill{{font:500 14px M;fill:{INK}}}
.tiny{{font:500 10px M;letter-spacing:.08em;fill:{INK};fill-opacity:.45}}
.coord{{font:500 11px M;letter-spacing:.14em;fill:{INK};fill-opacity:.7}}
.tick{{font:500 {TK_SIZE}px M;letter-spacing:{TK_LS}em;fill:{INK};fill-opacity:.38}}
.c{{fill:none;stroke:{PINK};stroke-linecap:round;animation:draw 2.6s cubic-bezier(.3,.6,.2,1) forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
.ping{{transform-origin:{PX}px {PY}px;animation:ping 5.5s cubic-bezier(.15,.6,.35,1) 2.4s infinite both}}
@keyframes ping{{0%{{transform:scale(0);opacity:1}}75%{{opacity:1}}100%{{transform:scale(1);opacity:0}}}}
.trail{{stroke-dasharray:1 9;animation:walk 1.4s linear infinite}}
@keyframes walk{{to{{stroke-dashoffset:-20}}}}
.trailin{{stroke-dasharray:900;stroke-dashoffset:900;animation:drawt 2.4s .9s ease-out forwards}}
@keyframes drawt{{to{{stroke-dashoffset:0}}}}
.aur1{{animation:a1 16s ease-in-out infinite alternate}}
.aur2{{animation:a2 21s ease-in-out infinite alternate}}
@keyframes a1{{to{{transform:translate(-120px,40px)}}}}
@keyframes a2{{to{{transform:translate(90px,-50px)}}}}
.up{{animation:up 1s cubic-bezier(.2,.9,.2,1) both}}
@keyframes up{{from{{transform:translateY(72px)}}to{{transform:none}}}}
.fade{{animation:fade 1s ease both}}
@keyframes fade{{from{{opacity:0}}}}
.dash{{transform-box:fill-box;transform-origin:left;animation:grow .9s .15s cubic-bezier(.2,.8,.2,1) both}}
@keyframes grow{{from{{transform:scaleX(0)}}}}
{"".join(type_css)}
.caret{{animation:caret {T}s linear infinite}}
@keyframes caret{{{"".join(caret_kf)}}}
.blink{{animation:blink 1s steps(1) infinite}}
@keyframes blink{{50%{{opacity:0}}}}
.ghost{{animation:bob 3.2s ease-in-out infinite alternate}}
@keyframes bob{{from{{transform:translateY(-3px)}}to{{transform:translateY(4px)}}}}
.shadow{{transform-box:fill-box;transform-origin:center;animation:shadow 3.2s ease-in-out infinite alternate}}
@keyframes shadow{{from{{transform:scaleX(.7);opacity:.25}}to{{transform:scaleX(1);opacity:.45}}}}
.eyes{{transform-box:fill-box;transform-origin:center;animation:eyes 6s 1.5s infinite}}
@keyframes eyes{{0%,86%,90%,100%{{transform:scaleY(1)}}88%{{transform:scaleY(.1)}}}}
.pulse{{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-out infinite}}
@keyframes pulse{{from{{transform:scale(1);opacity:.7}}to{{transform:scale(3.2);opacity:0}}}}
.ticker{{animation:ticker 40s linear infinite}}
@keyframes ticker{{to{{transform:translateX(-{TK_W:.2f}px)}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.c{{stroke-dashoffset:0!important}}.trailin{{stroke-dashoffset:0}}.ping{{opacity:0}}.t0{{transform:none}}}}
"""

ghost = f"""
<g transform="translate({PX} {PY})">
  <ellipse class="shadow" cx="0" cy="4" rx="11" ry="2.6" fill="#000"/>
  <g class="ghost">
    <path d="M-13 -6 v-17 a13 13 0 0 1 26 0 v17 l-4.3 -3.4 -4.4 3.4 -4.3 -3.4 -4.3 3.4 -4.4 -3.4 Z" fill="{INK}"/>
    <g class="eyes" fill="#1a0812"><ellipse cx="-4.6" cy="-21" rx="2.3" ry="3.2"/><ellipse cx="4.6" cy="-21" rx="2.3" ry="3.2"/></g>
  </g>
</g>"""

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Akhmad Noval Annur</title>
<desc id="d">Fullstack developer building React interfaces, Go backends and AI-powered tools. Informatics student at Telkom University Purwokerto. Portfolio: novala.my.id</desc>
<defs>
<style>{css}</style>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="20"/></clipPath>
<clipPath id="n1"><rect x="0" y="86" width="{W}" height="70"/></clipPath>
<clipPath id="n2"><rect x="0" y="156" width="{W}" height="72"/></clipPath>
<pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="12" cy="12" r="1" fill="{INK}" fill-opacity=".09"/></pattern>
<linearGradient id="fadeL" x1="0" x2="1"><stop offset=".38" stop-color="#fff" stop-opacity="0"/><stop offset=".62" stop-color="#fff"/></linearGradient>
<mask id="mapmask"><rect width="{W}" height="{H}" fill="url(#fadeL)"/></mask>
<linearGradient id="nameg" gradientUnits="userSpaceOnUse" x1="60" y1="0" x2="420" y2="0">
  <stop offset="0" stop-color="{DEEP}"/><stop offset=".42" stop-color="{PINK}"/><stop offset=".5" stop-color="#fde7f2"/><stop offset=".58" stop-color="{PINK}"/><stop offset="1" stop-color="{DEEP}"/>
  <animateTransform attributeName="gradientTransform" type="translate" values="-420 0;420 0" dur="5s" begin="1.6s" repeatCount="indefinite"/>
</linearGradient>
<radialGradient id="ring" cx="{PX}" cy="{PY}" r="560" gradientUnits="userSpaceOnUse">
  <stop offset=".80" stop-color="#fff" stop-opacity="0"/><stop offset=".93" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>
</radialGradient>
<mask id="pingmask"><circle class="ping" cx="{PX}" cy="{PY}" r="560" fill="url(#ring)"/></mask>
<radialGradient id="glow1"><stop offset="0" stop-color="{DEEP}" stop-opacity=".55"/><stop offset="1" stop-color="{DEEP}" stop-opacity="0"/></radialGradient>
<radialGradient id="glow2"><stop offset="0" stop-color="#9d174d" stop-opacity=".6"/><stop offset="1" stop-color="#9d174d" stop-opacity="0"/></radialGradient>
<linearGradient id="bandfade" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".08" stop-color="#fff"/><stop offset=".92" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="bandmask"><rect width="{W}" height="{H}" fill="url(#bandfade)"/></mask>
{"".join(masks)}
{"".join(paths)}
</defs>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="{BG}"/>
<g class="aur1"><ellipse cx="1040" cy="150" rx="420" ry="300" fill="url(#glow1)"/></g>
<g class="aur2"><ellipse cx="1220" cy="360" rx="320" ry="220" fill="url(#glow2)"/></g>
<rect width="{W}" height="{H}" fill="url(#dots)" mask="url(#mapmask)"/>

<g mask="url(#mapmask)">
  <g>{"".join(contours)}</g>
  <g mask="url(#pingmask)" fill="none" stroke="#ffd6ea" stroke-linecap="round">{"".join(highlights)}</g>
  <path class="trailin" d="{trail_d}" fill="none" stroke="{INK}" stroke-opacity=".12" stroke-width="5" stroke-linecap="round"/>
  <g class="fade" style="animation-delay:2.2s"><path class="trail" d="{trail_d}" fill="none" stroke="#fde7f2" stroke-opacity=".85" stroke-width="2.2" stroke-linecap="round"/></g>
</g>

<g class="fade" style="animation-delay:1.8s">
  <circle cx="{PX}" cy="{PY}" r="3.5" fill="{PINK}"/><circle cx="{PX}" cy="{PY}" r="3.5" fill="{PINK}" class="pulse"/>
  <path d="M{PX + 18} {PY - 30} L{PX + 46} {PY - 58} H{PX + 66}" fill="none" stroke="{INK}" stroke-opacity=".35"/>
  <text class="coord" x="{PX + 72}" y="{PY - 54}">07°25′S 109°14′E</text>
  <text class="tiny" x="{PX + 72}" y="{PY - 38}">YOU ARE HERE</text>
  {ghost}
</g>

<g class="fade" style="animation-delay:.05s">
  <rect class="dash" x="64" y="64" width="26" height="1.5" fill="{DEEP}"/>
  <text class="k" x="102" y="69">FULLSTACK DEVELOPER · PURWOKERTO, ID</text>
</g>
<g clip-path="url(#n1)"><g class="up" style="animation-delay:.2s"><text class="name" x="60" y="146">AKHMAD NOVAL</text></g></g>
<g clip-path="url(#n2)"><g class="up" style="animation-delay:.35s"><text class="name2" x="60" y="216" fill="url(#nameg)">ANNUR.</text></g></g>

<g class="fade" style="animation-delay:1s">
  <text class="pre" x="{TX}" y="{TY}">{PREFIX}</text>
  {"".join(role_svg)}
  <g class="caret"><rect class="blink" x="{RX + 1}" y="{TY - 17}" width="10" height="21" fill="{PINK}" fill-opacity=".85"/></g>
  <text class="meta" x="64" y="{TY + 38}">Informatics student at Telkom University Purwokerto</text>
</g>

<g class="fade" style="animation-delay:1.3s">
  <rect x="1052" y="36" width="180" height="38" rx="19" fill="{BG}" fill-opacity=".55" stroke="{INK}" stroke-opacity=".16"/>
  <circle cx="1074" cy="55" r="4" fill="{PINK}"/><circle cx="1074" cy="55" r="4" fill="{PINK}" class="pulse"/>
  <text class="pill" x="1088" y="60">novala.my.id ↗</text>
</g>

<g class="fade" style="animation-delay:1.5s">
  <rect y="{BAND}" width="{W}" height="{H - BAND}" fill="{BG}" fill-opacity=".82"/>
  <rect y="{BAND}" width="{W}" height="1" fill="{INK}" fill-opacity=".08"/>
  <g mask="url(#bandmask)"><g class="ticker">
    <text class="tick" x="0" y="{BAND + 29}">{STACK}</text>
    <text class="tick" x="{TK_W:.2f}" y="{BAND + 29}">{STACK}</text>
    <text class="tick" x="{2 * TK_W:.2f}" y="{BAND + 29}">{STACK}</text>
  </g></g>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="19.5" fill="none" stroke="{INK}" stroke-opacity=".08"/>
</g>
</svg>"""

out = ROOT / "assets" / "header.svg"
out.write_text(svg, encoding="utf-8")
print(out, f"{len(svg) / 1024:.0f} KB, {len(contours)} contour paths")
