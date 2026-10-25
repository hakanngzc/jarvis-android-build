#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb


def find_match_resume(path: Path):
    w, h, channels, rows = decode_png_rgb(path)

    # Stock NSS keeps the match screen active at half-time/full-time pauses and
    # renders a large football-shaped PLAY button in the lower-right corner.
    # Run165 proved that the TV panel above can also contain large neutral-white
    # team circles, so only inspect the lower-right resume-button region.
    x0, x1 = int(w * 0.72), w
    y0, y1 = int(h * 0.72), int(h * 0.88)
    if x1 <= x0 or y1 <= y0:
        return None

    neutral = 0
    green = 0
    total = (x1 - x0) * (y1 - y0)
    for y in range(y0, y1):
        row = rows[y]
        for x in range(x0, x1):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if r > 170 and g > 170 and b > 170 and max(r, g, b) - min(r, g, b) < 85:
                neutral += 1
            if g > 90 and g >= r + 25 and g >= b + 25:
                green += 1

    # The real run165 half-time frame measures about 14% neutral-bright and
    # 15% green in this region. A real run156 kick frame has enough neutral
    # stadium detail to be dangerous, but only ~0.3% green here. Requiring both
    # signals isolates the PLAY/football control without OCR or fixed pixels.
    if neutral < int(total * 0.08) or green < int(total * 0.06):
        return None

    # This normalized center is (934,1851) on the proven 1080x2280 Pixel4
    # profile, matching the stock match Play control used by the runtime gate.
    return round(w * 0.865), round(h * 0.812)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: find_match_resume.py SCREENSHOT.png')
    try:
        hit = find_match_resume(Path(sys.argv[1]))
    except Exception as exc:
        print(f'MATCH_RESUME_DETECT_ERROR={exc}', file=sys.stderr)
        raise SystemExit(2)
    if hit is None:
        raise SystemExit(1)
    print(hit[0], hit[1])


if __name__ == '__main__':
    main()
