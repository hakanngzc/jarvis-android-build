#!/usr/bin/env python3
"""Locate the NSS 4.31 MainMenu Play button visually without OCR.

The stock menu renders Play / Practice / Options as three wide green horizontal
buttons. We identify those bands in the central-lower viewport and choose the
first one (Play), then use the actual green extent to choose a safe center tap.
"""
from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image


def is_green(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return g >= 105 and g >= r * 1.25 and g >= b * 1.25


def pick(path: Path) -> tuple[int, int, list[tuple[int, int]]]:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    x0, x1 = int(w * 0.05), int(w * 0.98)
    step = max(1, w // 270)
    samples = max(1, (x1 - x0 + step - 1) // step)
    rows: list[int] = []
    for y in range(int(h * 0.48), int(h * 0.80), 2):
        green = sum(1 for x in range(x0, x1, step) if is_green(px[x, y]))
        if green / samples >= 0.20:
            rows.append(y)
    if not rows:
        raise SystemExit('No MainMenu green button rows detected')

    groups: list[tuple[int, int]] = []
    start = prev = rows[0]
    for y in rows[1:]:
        if y - prev <= 4:
            prev = y
        else:
            if prev - start >= max(20, int(h * 0.025)):
                groups.append((start, prev))
            start = prev = y
    if prev - start >= max(20, int(h * 0.025)):
        groups.append((start, prev))
    if len(groups) < 3:
        raise SystemExit(f'Expected Play/Practice/Options bands, found {groups}')

    y0, y1 = groups[0]
    y = (y0 + y1) // 2
    green_x = [x for x in range(x0, x1) if is_green(px[x, y])]
    if len(green_x) < int(w * 0.15):
        raise SystemExit('Play band green extent too small')
    x = (min(green_x) + max(green_x)) // 2
    return x, y, groups[:3]


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: pick_mainmenu_play.py screenshot.png output.txt')
    x, y, groups = pick(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(f'{x} {y}\n', encoding='utf-8')
    print(f'mainmenu_play_target {x} {y} bands {groups}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
