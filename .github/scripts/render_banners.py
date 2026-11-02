#!/usr/bin/env python3
"""Render lightweight, genuinely animated GIF banners for the GitHub README.

GitHub's image proxy can display SVG animation as a still image. Generating GIFs
here gives the profile dependable motion without client-side JavaScript.
"""
from __future__ import annotations

import io
import math
import re
from pathlib import Path

import cairosvg
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
OUTPUT = ASSETS / "animated"
WIDTH, HEIGHT = 1100, 190
FRAMES, FRAME_MS = 32, 120
OUTPUT.mkdir(parents=True, exist_ok=True)


def base_image(name: str) -> Image.Image:
    svg = (ASSETS / f"{name}.svg").read_text(encoding="utf-8")
    # Use the original artwork as a precise base, dropping SVG animation tags.
    svg = re.sub(r"<(?:animate|animateMotion|animateTransform)\\b[^>]*?/>", "", svg)
    svg = re.sub(r"<style>.*?</style>", "", svg, flags=re.DOTALL)
    png = cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                           output_width=WIDTH, output_height=HEIGHT)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def dot(d: ImageDraw.ImageDraw, x: float, y: float, rgb: tuple[int, int, int],
        size: float = 5, strength: float = 1.0) -> None:
    for radius, alpha in ((size * 3.0, 14), (size * 2.0, 35),
                          (size * 1.35, 80), (size, 245)):
        r = int(max(1, radius))
        d.ellipse((x-r, y-r, x+r, y+r), fill=(*rgb, int(alpha * strength)))


def footguard(d: ImageDraw.ImageDraw, t: float) -> None:
    y = 49 + (0.5 - 0.5 * math.cos(2 * math.pi * t)) * 74
    d.rounded_rectangle((733, y-6, 842, y+6), radius=5,
                        fill=(83, 221, 231, 24))
    d.line((736, y, 839, y), fill=(117, 247, 242, 185), width=2)
    dot(d, 869 + 45 * t, 84, (150, 247, 246), size=3.3,
        strength=0.5 + 0.5 * math.sin(math.pi * t))
    dot(d, 38 + 437 * t, 164, (101, 234, 235), size=2.4, strength=0.8)


def ecolink(d: ImageDraw.ImageDraw, t: float) -> None:
    theta = 2 * math.pi * t - math.pi / 2
    for n in range(5):
        a = theta - n * 0.105
        x = 800 + 52 * math.cos(a)
        y = 88 + 52 * math.sin(a)
        dot(d, x, y, (157, 250, 210), size=2.2 + 1.7 * (5-n)/5,
            strength=(5-n)/5)
    dot(d, 854 + 46*t, 88, (168, 255, 227), size=3.2,
        strength=0.55 + 0.45 * math.sin(math.pi*t))
    dot(d, 38 + 437*t, 164, (133, 237, 197), size=2.4, strength=0.8)


def on_path(points: list[tuple[float, float]], t: float) -> tuple[float, float]:
    step = t * (len(points) - 1)
    i = min(int(step), len(points) - 2)
    u = step - i
    x0, y0 = points[i]
    x1, y1 = points[i + 1]
    return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u


def skillmatch(d: ImageDraw.ImageDraw, t: float) -> None:
    a = [(778, 56), (896, 92), (999, 128)]
    b = [(999, 56), (896, 92), (778, 128)]
    x, y = on_path(a, t)
    dot(d, x, y, (224, 230, 255), size=5.1)
    x, y = on_path(b, (t + .5) % 1)
    dot(d, x, y, (138, 232, 247), size=4.4)
    dot(d, 896, 92, (166, 180, 254),
        size=3.6 + 1.2 * math.sin(2 * math.pi * t), strength=0.5)
    dot(d, 38 + 437*t, 164, (165, 176, 255), size=2.4, strength=0.8)


EFFECTS = {
    "footguard": footguard,
    "ecolink": ecolink,
    "skillmatch": skillmatch,
}

for name, effect in EFFECTS.items():
    base = base_image(name)
    # A consistent shared palette avoids GIF frame-to-frame color flicker.
    palette = base.convert("RGB").quantize(colors=192)
    frames = []
    for i in range(FRAMES):
        overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        effect(ImageDraw.Draw(overlay, "RGBA"), i / FRAMES)
        still = Image.alpha_composite(base, overlay).convert("RGB")
        frames.append(still.quantize(palette=palette, dither=Image.Dither.NONE))
    target = OUTPUT / f"{name}.gif"
    frames[0].save(target, save_all=True, append_images=frames[1:],
                   duration=FRAME_MS, loop=0, optimize=True, disposal=2)
    check = Image.open(target)
    assert check.n_frames >= 20, f"{name}: expected animation; got {check.n_frames} frames"
    print(f"{name}: {check.n_frames} frames; {target.stat().st_size:,} bytes")
