#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb


def find_kick_ball(path: Path):
    w, h, channels, rows = decode_png_rgb(path)
    # NSS live chances render the player-controlled ball as a very large,
    # high-contrast white/black sphere in the lower-middle pitch. Run165 also
    # proved that the half-time TV panel contains large neutral-white team
    # circles around ~44% screen height, so start the kick search below 55%.
    win = max(180, min(320, w // 4))
    stride = max(12, w // 54)
    x_min = int(w * 0.12)
    x_max = int(w * 0.88) - win
    y_min = int(h * 0.55)
    y_max = int(h * 0.82) - win
    if x_max <= x_min or y_max <= y_min:
        return None

    bright = bytearray(w * h)
    for y, row in enumerate(rows):
        base = y * w
        for x in range(w):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if r > 170 and g > 170 and b > 170 and max(r, g, b) - min(r, g, b) < 85:
                bright[base + x] = 1

    # Row-prefix sums keep the scan cheap in the emulator runtime and avoid
    # adding Pillow/numpy to the evidence harness.
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

    # The real run156 kick frame remains ~62% neutral-bright after the lower
    # pitch restriction. 25% leaves margin for shaded/black ball panels while
    # rejecting ordinary player sprites and pitch furniture.
    if best is None or best_count < int(win * win * 0.25):
        return None
    return best


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: find_kick_ball.py SCREENSHOT.png')
    result = find_kick_ball(Path(sys.argv[1]))
    if result is None:
        raise SystemExit(1)
    print(result[0], result[1])


if __name__ == '__main__':
    main()
