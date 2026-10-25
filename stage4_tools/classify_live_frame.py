#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb
from find_kick_ball import _find_compact_field_ball


def _find_live_component(w: int, h: int, mask: bytearray):
    y0, y1 = int(h * 0.25), int(h * 0.88)
    best = None
    best_count = -1
    for y in range(y0, y1):
        for x in range(w):
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
                if cx > 0:
                    n = idx - 1
                    if mask[n]:
                        mask[n] = 0
                        stack.append(n)
                if cx + 1 < w:
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
            bw, bh = maxx - minx + 1, maxy - miny + 1
            if not (25 <= bw <= 180 and 25 <= bh <= 180 and count >= 120):
                continue
            aspect = bw / bh
            density = count / (bw * bh)
            if not (0.70 <= aspect <= 1.40 and density >= 0.08):
                continue
            if count > best_count:
                best_count = count
                best = (round((minx + maxx) / 2), round((miny + maxy) / 2))
    return best


def _find_large_kick_ball(w: int, h: int, bright: bytearray):
    win = max(180, min(320, w // 4))
    stride = max(12, w // 54)
    x_min = int(w * 0.12)
    x_max = int(w * 0.88) - win
    center_y_min = int(h * 0.68)
    center_y_max = int(h * 0.80)
    y_min = max(0, center_y_min - win // 2)
    y_max = min(h - win, center_y_max - win // 2)
    if x_max <= x_min or y_max < y_min:
        return None

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
    return None


def classify_live_frame(path: Path, include_size: bool = False):
    w, h, channels, rows = decode_png_rgb(path)

    def result(kind: str, x: int, y: int):
        if include_size:
            return kind, x, y, w, h
        return kind, x, y

    # Resume is highest-priority and cheap to test once the PNG is decoded.
    rx0, rx1 = int(w * 0.72), w
    ry0, ry1 = int(h * 0.72), int(h * 0.88)
    neutral = green = 0
    total = max(1, (rx1 - rx0) * (ry1 - ry0))
    for y in range(ry0, ry1):
        row = rows[y]
        for x in range(rx0, rx1):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if r > 170 and g > 170 and b > 170 and max(r, g, b) - min(r, g, b) < 85:
                neutral += 1
            if g > 90 and g >= r + 25 and g >= b + 25:
                green += 1
    if neutral >= int(total * 0.08) and green >= int(total * 0.01):
        return result('resume', round(w * 0.865), round(h * 0.812))

    # Build both masks in one pass. Older harnesses decoded the same frame
    # independently for resume/live/kick classification; this keeps one PNG
    # decode and also lets the CLI return the exact rendered dimensions so the
    # input driver can scale swipes after an Android wm-size override.
    live_y0, live_y1 = int(h * 0.25), int(h * 0.88)
    live = bytearray(w * h)
    bright = bytearray(w * h)
    for y, row in enumerate(rows):
        base = y * w
        live_row = live_y0 <= y < live_y1
        for x in range(w):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if live_row and 45 <= g <= 135 and r <= 45 and b <= 45 and g >= r + 25 and g >= b + 25:
                live[base + x] = 1
            if r > 170 and g > 170 and b > 170 and max(r, g, b) - min(r, g, b) < 85:
                bright[base + x] = 1

    hit = _find_live_component(w, h, live)
    if hit is not None:
        return result('live', hit[0], hit[1])

    hit = _find_large_kick_ball(w, h, bright)
    if hit is None:
        hit = _find_compact_field_ball(w, h, bright)
    if hit is not None:
        return result('kick', hit[0], hit[1])

    return None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: classify_live_frame.py SCREENSHOT.png')
    try:
        hit = classify_live_frame(Path(sys.argv[1]), include_size=True)
    except Exception as exc:
        print(f'LIVE_FRAME_CLASSIFY_ERROR={exc}', file=sys.stderr)
        raise SystemExit(2)
    if hit is None:
        raise SystemExit(1)
    print(hit[0], hit[1], hit[2], hit[3], hit[4])


if __name__ == '__main__':
    main()
