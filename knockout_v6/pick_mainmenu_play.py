#!/usr/bin/env python3
"""Locate MainMenu Play only after the stock three-button menu has settled."""
from __future__ import annotations

import subprocess
import sys
import time
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

    groups: list[tuple[int, int]] = []
    if rows:
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

    # A one-band frame is the stock slide-in animation, not a stable menu.
    if len(groups) < 3:
        raise ValueError(f'MainMenu not settled: expected >=3 action bands, found {groups}')

    y0, y1 = groups[0]
    y = (y0 + y1) // 2
    green_x = [x for x in range(x0, x1) if is_green(px[x, y])]
    if len(green_x) < int(w * 0.15):
        raise ValueError('Play band green extent too small')
    if max(green_x) - min(green_x) < int(w * 0.25):
        raise ValueError('Play band width too small')
    x = (min(green_x) + max(green_x)) // 2
    return x, y, groups


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: pick_mainmenu_play.py screenshot.png output.txt')
    path = Path(sys.argv[1])
    out = Path(sys.argv[2])
    last: Exception | None = None
    for attempt in range(1, 13):
        try:
            x, y, groups = pick(path)
            out.write_text(f'{x} {y}\n', encoding='utf-8')
            print(f'mainmenu_play_target {x} {y} bands {groups} attempt {attempt}')
            return 0
        except Exception as exc:
            last = exc
            if attempt == 12:
                break
            # Refresh the same evidence frame and wait for stock slide-in animation.
            with path.open('wb') as f:
                subprocess.run(
                    ['adb', 'exec-out', 'screencap', '-p'],
                    stdout=f,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            time.sleep(1)
    raise SystemExit(f'MainMenu did not settle: {last}')


if __name__ == '__main__':
    raise SystemExit(main())
