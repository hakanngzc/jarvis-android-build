#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb


def find_andorra_row(path: Path):
    w, h, channels, rows = decode_png_rgb(path)
    y0, y1 = int(h * 0.18), int(h * 0.72)
    x0, x1 = int(w * 0.15), int(w * 0.85)
    mask = bytearray(w * h)
    for y in range(y0, y1):
        row = rows[y]
        base = y * w
        for x in range(x0, x1):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if g > 85 and g >= r + 45 and g >= b + 50 and r < 150 and b < 120:
                mask[base + x] = 1

    components = []
    for y in range(y0, y1):
        for x in range(x0, x1):
            start = y * w + x
            if not mask[start]:
                continue
            stack = [start]
            mask[start] = 0
            count = 0
            minx = maxx = x
            miny = maxy = y
            while stack:
                idx = stack.pop()
                cy, cx = divmod(idx, w)
                count += 1
                minx = min(minx, cx)
                maxx = max(maxx, cx)
                miny = min(miny, cy)
                maxy = max(maxy, cy)
                if cx > x0:
                    n = idx - 1
                    if mask[n]:
                        mask[n] = 0
                        stack.append(n)
                if cx + 1 < x1:
                    n = idx + 1
                    if mask[n]:
                        mask[n] = 0
                        stack.append(n)
                if cy > y0:
                    n = idx - w
                    if mask[n]:
                        mask[n] = 0
                        stack.append(n)
                if cy + 1 < y1:
                    n = idx + w
                    if mask[n]:
                        mask[n] = 0
                        stack.append(n)
            box_w = maxx - minx + 1
            box_h = maxy - miny + 1
            if (
                int(w * 0.45) <= box_w <= int(w * 0.72)
                and int(h * 0.035) <= box_h <= int(h * 0.08)
                and count > int(w * h * 0.004)
            ):
                components.append(((miny + maxy) // 2, (minx + maxx) // 2))

    components.sort()
    # Stock selector top rows are Albania, Algeria, Andorra, Angola, Argentina,
    # Armenia. Andorra is therefore the third rendered row.
    if len(components) < 5:
        return None
    y, x = components[2]
    return x, y


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: find_league_picker.py SCREENSHOT.png')
    try:
        hit = find_andorra_row(Path(sys.argv[1]))
    except Exception as exc:
        print(f'LEAGUE_PICKER_DETECT_ERROR={exc}', file=sys.stderr)
        raise SystemExit(2)
    if hit is None:
        raise SystemExit(1)
    print(hit[0], hit[1])


if __name__ == '__main__':
    main()
