#!/usr/bin/env python3
from PIL import Image
import sys

if len(sys.argv) != 3:
    raise SystemExit('usage: detect_stock_play.py SCREENSHOT OUT_TARGET')

im = Image.open(sys.argv[1]).convert('RGB')
w, h = im.size
x0, x1 = int(w * .35), int(w * .98)
y0, y1 = int(h * .50), int(h * .86)

def green(p):
    r, g, b = p
    return g >= 95 and g - r >= 25 and g - b >= 20 and g >= r * 1.15

rows = []
for y in range(y0, y1, 2):
    hits = sum(green(im.getpixel((x, y))) for x in range(x0, x1, 3))
    if hits >= 60:
        rows.append(y)
if not rows:
    raise SystemExit('stock Play/action bands not detected')

groups = []
for y in rows:
    if not groups or y - groups[-1][-1] > 4:
        groups.append([y])
    else:
        groups[-1].append(y)
groups = [g for g in groups if g[-1] - g[0] >= 45]
if len(groups) < 4:
    raise SystemExit(f'stock menu action-band fingerprint incomplete: {[(g[0], g[-1]) for g in groups]}')

first = groups[0]
ya, yb = first[0], first[-1]
pts = []
for y in range(ya, yb + 1, 3):
    for x in range(x0, x1, 3):
        if green(im.getpixel((x, y))):
            pts.append((x, y))
if len(pts) < 500:
    raise SystemExit('stock Play band has too few green pixels')

xs = sorted(x for x, _ in pts)
ys = sorted(y for _, y in pts)
x = xs[len(xs) // 2]
y = ys[len(ys) // 2]
open(sys.argv[2], 'w').write(f'{x} {y}\n')
print('stock_play_target', x, y, 'bands', [(g[0], g[-1]) for g in groups[:4]])
