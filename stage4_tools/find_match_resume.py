#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb


def find_match_resume(path: Path):
    w, h, channels, rows = decode_png_rgb(path)

    # Stock NSS keeps the match screen active at half-time/full-time pauses and
    # renders a large football-shaped PLAY/continue button in the lower-right.
    # Run165 proved the half-time TV panel can contain large neutral-white team
    # circles, so only inspect the lower-right resume-button region.
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

    # Half-time run165 measured ~14% neutral / ~6.2% green here. The real
    # run171 90' Full Time continue control measured ~21.7% neutral / ~2.7%
    # green, while normal kickoff and the run170 field frame measured 0% for
    # both in this region. Keep the neutral requirement and lower only the
    # green floor enough to include the verified Full Time variant.
    if neutral < int(total * 0.08) or green < int(total * 0.01):
        return None

    # This normalized center is (934,1851) on the proven 1080x2280 Pixel4
    # profile, matching the stock match Play/continue control.
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
