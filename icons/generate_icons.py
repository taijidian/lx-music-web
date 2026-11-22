#!/usr/bin/env python3
"""Generate the PWA PNG icons (same artwork as icon.svg).

Usage:  pip install pillow && python3 icons/generate_icons.py
Outputs icon-180.png / icon-192.png / icon-512.png / icon-maskable-512.png
into this directory. The maskable variant adds safe-zone padding.
"""
from PIL import Image, ImageDraw

TOP = (124, 92, 255)      # gradient start
BOTTOM = (0, 194, 168)    # gradient end


def gradient(size):
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            t = (x + y) / (2 * size)
            px[x, y] = tuple(int(TOP[i] + (BOTTOM[i] - TOP[i]) * t) for i in range(3))
    return img


def draw_icon(size, pad_ratio):
    scale = 4  # supersample for smooth edges
    S = size * scale
    img = gradient(S).convert("RGBA")
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    pad = int(S * 0.03)
    md.rounded_rectangle([pad, pad, S - pad, S - pad], radius=int(S * 0.22), fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)

    d = ImageDraw.Draw(out)
    inner = 1.0 - 2 * pad_ratio          # note size relative to canvas
    ox = S * pad_ratio                    # note offset
    u = S * inner / 512.0                 # unit from the 512 viewBox

    def P(x, y):
        return (ox + x * u, ox + y * u)

    def ellipse(cx, cy, rx, ry):
        x, y = P(cx, cy)
        d.ellipse([x - rx * u, y - ry * u, x + rx * u, y + ry * u], fill=(255, 255, 255, 255))

    def rect(x, y, w, h):
        x0, y0 = P(x, y)
        d.rectangle([x0, y0, x0 + w * u, y0 + h * u], fill=(255, 255, 255, 255))

    ellipse(196, 348, 52, 40)
    ellipse(356, 318, 52, 40)
    rect(238, 128, 18, 224)
    rect(398, 98, 18, 224)
    x0, y0 = P(238, 128)
    x1, y1 = P(416, 98)
    x2, y2 = P(416, 168)
    x3, y3 = P(238, 198)
    d.polygon([(x0, y0), (x1, y1), (x2, y2), (x3, y3)], fill=(255, 255, 255, 255))

    return out.resize((size, size), Image.LANCZOS)


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    for name, size, pad in [
        ("icon-180.png", 180, 0.0),
        ("icon-192.png", 192, 0.0),
        ("icon-512.png", 512, 0.0),
        ("icon-maskable-512.png", 512, 0.10),
    ]:
        draw_icon(size, pad).save(os.path.join(here, name))
        print("wrote", name)
