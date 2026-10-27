#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb


def find_dilemma_choice(path: Path):
    w, h, channels, rows = decode_png_rgb(path)
    x0, x1 = int(w * 0.10), int(w * 0.90)
    y0, y1 = int(h * 0.30), int(h * 0.82)
    mask = bytearray(w * h)

    # Stock Dilemma choices contain broad yellow/gold selection bars.  Run182
    # rendered two of them (FANS/BOSS); choose the upper rendered choice.
    for y in range(y0, y1):
        row = rows[y]
        base = y * w
        for x in range(x0, x1):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if r > 180 and g > 110 and b < 120 and r - b > 100 and g - b > 60:
                mask[base + x] = 1

    candidates = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            idx = y * w + x
            if not mask[idx]:
                continue
            stack = [idx]
            mask[idx] = 0
            count = 0
            minx = maxx = x
            miny = maxy = y
            sx = sy = 0
            while stack:
                cur = stack.pop()
                cy, cx = divmod(cur, w)
                count += 1
                sx += cx
                sy += cy
                minx = min(minx, cx); maxx = max(maxx, cx)
                miny = min(miny, cy); maxy = max(maxy, cy)
                if cx > x0:
                    n = cur - 1
                    if mask[n]: mask[n] = 0; stack.append(n)
                if cx + 1 < x1:
                    n = cur + 1
                    if mask[n]: mask[n] = 0; stack.append(n)
                if cy > y0:
                    n = cur - w
                    if mask[n]: mask[n] = 0; stack.append(n)
                if cy + 1 < y1:
                    n = cur + w
                    if mask[n]: mask[n] = 0; stack.append(n)
            bw = maxx - minx + 1
            bh = maxy - miny + 1
            if (
                int(w * 0.25) <= bw <= int(w * 0.65)
                and int(h * 0.015) <= bh <= int(h * 0.060)
                # Run #298's two valid stock bars contain ~0.88% of the full
                # frame as thresholded gold pixels. Keep the strict stock bar
                # geometry above while accepting that naturally sparse fill.
                and count >= int(w * h * 0.008)
            ):
                candidates.append((sy / count, sx / count, count))

    if not candidates:
        return None
    candidates.sort()
    y, x, _ = candidates[0]
    return round(x), round(y)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: find_dilemma_choice.py SCREENSHOT.png')
    try:
        hit = find_dilemma_choice(Path(sys.argv[1]))
    except Exception as exc:
        print(f'DILEMMA_DETECT_ERROR={exc}', file=sys.stderr)
        raise SystemExit(2)
    if hit is None:
        raise SystemExit(1)
    print(hit[0], hit[1])


if __name__ == '__main__':
    main()
