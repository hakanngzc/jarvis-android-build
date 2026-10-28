#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb


def _find_compact_field_ball(w: int, h: int, bright: bytearray):
    # Later natural chances can render the playable football at normal field
    # scale rather than the earlier giant kick-ball scale. Run170 reached 80'
    # with a real ~28x26 px football in the lower field. Search only the actual
    # playing field above the sponsor strip proven by run185.
    x0, x1 = int(w * 0.08), int(w * 0.92)
    y0, y1 = int(h * 0.55), int(h * 0.79)
    min_dim = max(10, int(w * 0.012))
    max_dim = max(24, int(w * 0.065))
    min_count = max(20, int(w * w * 0.00008))
    mask = bytearray(bright)
    best = None
    best_count = -1

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
                if cx < minx: minx = cx
                if cx > maxx: maxx = cx
                if cy < miny: miny = cy
                if cy > maxy: maxy = cy
                for dy in (-1, 0, 1):
                    ny = cy + dy
                    if ny < y0 or ny >= y1:
                        continue
                    for dx in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx = cx + dx
                        if nx < x0 or nx >= x1:
                            continue
                        n = ny * w + nx
                        if mask[n]:
                            mask[n] = 0
                            stack.append(n)

            bw = maxx - minx + 1
            bh = maxy - miny + 1
            if not (min_dim <= bw <= max_dim and min_dim <= bh <= max_dim):
                continue
            if count < min_count:
                continue
            aspect = bw / bh
            density = count / (bw * bh)
            if not (0.75 <= aspect <= 1.33 and density >= 0.22):
                continue
            if count > best_count:
                best_count = count
                best = (round((minx + maxx) / 2), round((miny + maxy) / 2))
    return best


def find_kick_ball(path: Path):
    w, h, channels, rows = decode_png_rgb(path)
    # Scale the large-ball search window with the rendered frame. At the
    # original Pixel4 width (1080) this remains 270 px. The natural-runtime
    # low-resolution surface uses width 540, yielding 135 px with equivalent
    # normalized geometry instead of the old hard 180 px minimum.
    win = max(90, min(320, w // 4))
    stride = max(6, w // 54)
    x_min = int(w * 0.12)
    x_max = int(w * 0.88) - win
    center_y_min = int(h * 0.68)
    center_y_max = int(h * 0.80)
    y_min = max(0, center_y_min - win // 2)
    y_max = min(h - win, center_y_max - win // 2)

    bright = bytearray(w * h)
    for y, row in enumerate(rows):
        base = y * w
        for x in range(w):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if r > 170 and g > 170 and b > 170 and max(r, g, b) - min(r, g, b) < 85:
                bright[base + x] = 1

    if x_max > x_min and y_max >= y_min:
        row_prefix = []
        for y in range(h):
            row = [0] * (w + 1)
            total = 0
            base = y * w
            for x in range(w):
                total += bright[base + x]
                row[x + 1] = total
            row_prefix.append(row)

        best = None
        best_count = 0
        for y0 in range(y_min, y_max + 1, stride):
            y1 = y0 + win
            for x0 in range(x_min, x_max + 1, stride):
                x1 = x0 + win
                count = 0
                for y in range(y0, y1):
                    row = row_prefix[y]
                    count += row[x1] - row[x0]
                if count > best_count:
                    best_count = count
                    best = (x0 + win // 2, y0 + win // 2)

        if best is not None and best_count >= int(win * win * 0.25):
            return best

    return _find_compact_field_ball(w, h, bright)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: find_kick_ball.py SCREENSHOT.png')
    result = find_kick_ball(Path(sys.argv[1]))
    if result is None:
        raise SystemExit(1)
    print(result[0], result[1])


if __name__ == '__main__':
    main()
