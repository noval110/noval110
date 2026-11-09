#!/usr/bin/env python3
"""Builds assets/header.svg, the animated profile header.

Pure SVG + CSS animation: GitHub shows README SVG images animated. Fonts are subset and
embedded as base64 so the text renders the same everywhere without external requests.

Usage: python .github/scripts/build_header.py <fonts_dir>
       fonts_dir holds unbounded.woff2, jakarta.woff2 and mono.woff2 (latin, variable)
Requires: pip install fonttools brotli
"""
import base64
import io
import math
import random
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[2]
FONTS = Path(sys.argv[1])
W, H = 1280, 400
CHARS = "".join(chr(c) for c in range(32, 127)) + "—·°′’"


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
rnd = random.Random(7)

# Sun / peak position
SX, SY = 1010, 214

# ---- contour rings around the peak (noise-wobbled closed curves) that draw themselves
CX, CY = 1010, 300
harm = [(rnd.uniform(0, 6.28), rnd.uniform(0.04, 0.09), k) for k in (2, 3, 5)]
rings = []
for i in range(9):
    rx, ry = 70 + i * 46, 38 + i * 27
    pts = []
    for s in range(72):
        a = s / 72 * math.tau
        w = 1 + sum(amp * math.sin(k * a + ph + i * 0.35) for ph, amp, k in harm)
        pts.append((CX + math.cos(a) * rx * w, CY + math.sin(a) * ry * w))
    d = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"
    rings.append(f'<path class="ring" style="animation-delay:{i * 0.22:.2f}s" d="{d}"/>')


def ridge(points, fill, cls=""):
    d = "M" + " L".join(f"{x} {y}" for x, y in points) + f" L{W + 120} {H} L-120 {H}Z"
    return f'<path class="{cls}" fill="{fill}" d="{d}"/>'


far = ridge([(-120, 334), (60, 322), (200, 330), (360, 312), (480, 318), (620, 270), (760, 286), (900, 214),
             (1010, 186), (1130, 238), (1280, 220), (1400, 250)], "#2a1424", "far")
mid = ridge([(-120, 352), (120, 340), (280, 350), (430, 330), (600, 324), (760, 288), (930, 326), (1060, 280),
             (1200, 312), (1400, 296)], "#1c0d18", "mid")
near = ridge([(-120, 372), (160, 346), (330, 364), (520, 334), (700, 362), (880, 342), (1060, 368), (1240, 344),
              (1400, 360)], "#0b060a")

rays = []
for i in range(14):
    a = i * math.tau / 14 + rnd.uniform(-0.1, 0.1)
    p1 = (SX + 700 * math.cos(a - 0.03), SY + 700 * math.sin(a - 0.03))
    p2 = (SX + 700 * math.cos(a + 0.03), SY + 700 * math.sin(a + 0.03))
    rays.append(f'<path d="M{SX} {SY} L{p1[0]:.0f} {p1[1]:.0f} L{p2[0]:.0f} {p2[1]:.0f}Z" fill="#ffe8d6" opacity=".18"/>')

mist = "".join(
    f'<ellipse cx="{x}" cy="{300 + (i % 3) * 8}" rx="{rnd.randint(90, 160)}" ry="16"/>'
    for i, x in enumerate(range(0, 1921, 160))
)

# ---- rotating role ticker: hold, slide up; the last line repeats the first for a seamless loop
ROLES = ["React interfaces", "Go backends", "AI-powered tools", "things that ship"]
LH = 30
role_text = "".join(f'<text class="role" x="0" y="{i * LH}">{r}</text>' for i, r in enumerate(ROLES + ROLES[:1]))
n = len(ROLES)
kf = []
for i in range(n):
    start, hold_end = i / n * 100, (i + 0.8) / n * 100
    kf.append(f"{start:.2f}%,{hold_end:.2f}%{{transform:translateY({-LH * i}px)}}")
kf.append(f"100%{{transform:translateY({-LH * n}px)}}")
ticker_kf = "".join(kf)

css = f"""
@font-face{{font-family:U;src:url(data:font/woff2;base64,{U}) format('woff2');font-weight:200 900}}
@font-face{{font-family:J;src:url(data:font/woff2;base64,{J}) format('woff2');font-weight:200 800}}
@font-face{{font-family:M;src:url(data:font/woff2;base64,{M}) format('woff2');font-weight:100 800}}
.k{{font:500 12px M;letter-spacing:.32em;fill:#f8f0f5;opacity:.55}}
.name{{font:800 60px U;letter-spacing:-1px;fill:#f8f0f5}}
.lead{{font:500 20px J;fill:#f8f0f5;opacity:.8}}
.role{{font:700 20px J;fill:#f472b6}}
.pill{{font:500 14px M;fill:#f8f0f5}}
.ring{{fill:none;stroke:#f472b6;stroke-width:1.1;stroke-dasharray:1400;stroke-dashoffset:1400;opacity:0;animation:draw 9s ease-in-out infinite}}
@keyframes draw{{0%{{stroke-dashoffset:1400;opacity:0}}12%{{opacity:.28}}45%{{stroke-dashoffset:0;opacity:.28}}80%{{stroke-dashoffset:0;opacity:.22}}100%{{stroke-dashoffset:0;opacity:0}}}}
.up{{animation:up 1s cubic-bezier(.2,.9,.2,1.15) both}}
@keyframes up{{from{{transform:translateY(80px)}}to{{transform:none}}}}
.fade{{animation:fade 1.2s ease both}}
@keyframes fade{{from{{opacity:0}}}}
.line{{transform-box:fill-box;transform-origin:left;animation:grow 1s .2s cubic-bezier(.2,.8,.2,1) both}}
@keyframes grow{{from{{transform:scaleX(0)}}}}
.ticker{{animation:tick 10s cubic-bezier(.7,0,.3,1) 1.4s infinite}}
@keyframes tick{{{ticker_kf}}}
.sun{{animation:rise 2.4s cubic-bezier(.2,.8,.2,1) both}}
@keyframes rise{{from{{transform:translateY(70px)}}}}
.halo{{transform-origin:{SX}px {SY}px;animation:breathe 6s ease-in-out infinite}}
@keyframes breathe{{50%{{transform:scale(1.12);opacity:.75}}}}
.rays{{transform-origin:{SX}px {SY}px;animation:spin 80s linear infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
.mid{{animation:drift 14s ease-in-out infinite alternate}}
.far{{animation:drift 22s ease-in-out infinite alternate-reverse}}
@keyframes drift{{to{{transform:translateX(-36px)}}}}
.mist{{animation:mist 26s linear infinite}}
@keyframes mist{{to{{transform:translateX(-640px)}}}}
.flock{{animation:fly 16s linear infinite}}
@keyframes fly{{from{{transform:translate(-160px,0)}}to{{transform:translate(1440px,-60px)}}}}
.wing{{transform-box:fill-box;transform-origin:center;animation:flap .5s ease-in-out infinite alternate}}
@keyframes flap{{to{{transform:scaleY(-.6)}}}}
.ghost{{animation:peek 7s cubic-bezier(.5,0,.3,1.4) 2s infinite both}}
@keyframes peek{{0%,62%,100%{{transform:translateY(46px)}}70%,92%{{transform:translateY(0)}}}}
.eyes{{transform-box:fill-box;transform-origin:center;animation:blink 7s 2s infinite}}
@keyframes blink{{0%,80%,84%,100%{{transform:scaleY(1)}}82%{{transform:scaleY(.1)}}}}
.pulse{{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-out infinite}}
@keyframes pulse{{from{{transform:scale(1);opacity:.6}}to{{transform:scale(3);opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.ring{{stroke-dashoffset:0;opacity:.22}}}}
"""

svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Akhmad Noval Annur</title>
<desc id="d">Fullstack developer building React interfaces, Go backends and AI-powered tools. Informatics student at Telkom University Purwokerto. Portfolio: novala.my.id</desc>
<defs>
<style>{css}</style>
<radialGradient id="glow" cx="{SX}" cy="{SY}" r="420" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#db2777" stop-opacity=".5"/><stop offset=".5" stop-color="#db2777" stop-opacity=".12"/><stop offset="1" stop-color="#db2777" stop-opacity="0"/></radialGradient>
<radialGradient id="sun" cx="50%" cy="50%" r="50%"><stop offset=".55" stop-color="#fff4ea"/><stop offset=".75" stop-color="#ffd9c2"/><stop offset="1" stop-color="#ffd9c2" stop-opacity="0"/></radialGradient>
<radialGradient id="raymask" cx="{SX}" cy="{SY}" r="300" gradientUnits="userSpaceOnUse"><stop offset="0" stop-color="#fff" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
<mask id="rm"><rect width="{W}" height="{H}" fill="url(#raymask)"/></mask>
<filter id="blur" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="14"/></filter>
<clipPath id="frame"><rect width="{W}" height="{H}" rx="18"/></clipPath>
<clipPath id="win"><rect x="0" y="-22" width="420" height="30"/></clipPath>
<clipPath id="n1"><rect x="0" y="80" width="{W}" height="76"/></clipPath>
<clipPath id="n2"><rect x="0" y="156" width="{W}" height="76"/></clipPath>
</defs>
<g clip-path="url(#frame)">
<rect width="{W}" height="{H}" fill="#0b060a"/>
<rect width="{W}" height="{H}" fill="url(#glow)" class="halo"/>
<g>{"".join(rings)}</g>
<g mask="url(#rm)"><g class="rays" opacity=".5">{"".join(rays)}</g></g>
<g class="sun"><circle cx="{SX}" cy="{SY}" r="78" fill="url(#sun)"/></g>
<g class="flock" fill="none" stroke="#0b060a" stroke-width="2" stroke-linecap="round">
  <g transform="translate(0 120)"><path class="wing" d="M-9 0 Q-4 -5 0 0 Q4 -5 9 0"/></g>
  <g transform="translate(-28 132)"><path class="wing" style="animation-delay:-.2s" d="M-7 0 Q-3 -4 0 0 Q3 -4 7 0"/></g>
  <g transform="translate(-22 108)"><path class="wing" style="animation-delay:-.35s" d="M-7 0 Q-3 -4 0 0 Q3 -4 7 0"/></g>
  <g transform="translate(-52 140)"><path class="wing" style="animation-delay:-.1s" d="M-6 0 Q-3 -3.5 0 0 Q3 -3.5 6 0"/></g>
</g>
{far}
<g class="mist" opacity=".18" filter="url(#blur)" fill="#f8e8f0">{mist}</g>
{mid}
<g class="ghost">
  <path d="M1172 352 v-26 a24 24 0 0 1 48 0 v26 Z" fill="#f8f0f5"/>
  <g class="eyes" fill="#1a0812"><ellipse cx="1188" cy="328" rx="3.6" ry="5"/><ellipse cx="1204" cy="328" rx="3.6" ry="5"/></g>
</g>
{near}
<g class="fade" style="animation-delay:.1s">
  <rect x="64" y="58" width="28" height="1.5" fill="#db2777" class="line"/>
  <text class="k" x="104" y="63">PORTFOLIO — '26 · PURWOKERTO, ID</text>
</g>
<g clip-path="url(#n1)"><g class="up" style="animation-delay:.25s"><text class="name" x="60" y="146">AKHMAD NOVAL</text></g></g>
<g clip-path="url(#n2)"><g class="up" style="animation-delay:.4s"><text class="name" x="60" y="222">ANNUR</text></g></g>
<g class="fade" style="animation-delay:.9s">
  <text class="lead" x="64" y="276">Fullstack developer building</text>
  <g transform="translate(343 276)"><g clip-path="url(#win)"><g class="ticker">{role_text}</g></g></g>
  <text class="lead" x="64" y="306" style="opacity:.6">Informatics student · Telkom University Purwokerto</text>
</g>
<g class="fade" style="animation-delay:1.2s">
  <rect x="1060" y="40" width="168" height="38" rx="19" fill="#f8f0f5" fill-opacity=".08" stroke="#f8f0f5" stroke-opacity=".18"/>
  <circle cx="1082" cy="59" r="4" fill="#f472b6"/><circle cx="1082" cy="59" r="4" fill="#f472b6" class="pulse"/>
  <text class="pill" x="1096" y="64">novala.my.id</text>
</g>
</g>
</svg>"""

out = ROOT / "assets" / "header.svg"
out.write_text(svg, encoding="utf-8")
print(out, f"{len(svg) / 1024:.0f} KB")
