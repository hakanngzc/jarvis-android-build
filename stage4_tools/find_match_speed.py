#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import decode_png_rgb


def _classify_pixel(r: int, g: int, b: int):
    # Exact stock match.uis colours, with tolerance for scaling/antialiasing:
    # 1200 -> #FFFF1D, 800 -> #FF6C00, 350 -> #FE1717.
    if r >= 190 and g >= 175 and b <= 100:
        return 1200
    if r >= 190 and 55 <= g <= 165 and b <= 90:
        return 800
    if r >= 175 and g <= 85 and b <= 85:
        return 350
    return None


def find_match_speed(path: Path):
    w, h, channels, rows = decode_png_rgb(path)

    # match.uis places TimeButton in the upper-right header at
    # PushOrigin:(535,7+[@T*0.7]). The normalized crop remains valid on the
    # proven Pixel4 full-resolution surface and is deliberately narrow to avoid
    # score/team-colour noise elsewhere in the header.
    x0, x1 = int(w * 0.82), int(w * 0.985)
    y0, y1 = int(h * 0.025), int(h * 0.155)
    if x1 <= x0 or y1 <= y0:
        return None

    hits = {1200: [], 800: [], 350: []}
    for y in range(y0, y1):
        row = rows[y]
        for x in range(x0, x1):
            i = x * channels
            speed = _classify_pixel(row[i], row[i + 1], row[i + 2])
            if speed is not None:
                hits[speed].append((x, y))

    # A rendered ISpeed glyph contributes many pixels. Ignore tiny isolated
    # colour noise and choose the strongest stock-speed colour cluster.
    speed, points = max(hits.items(), key=lambda item: len(item[1]))
    if len(points) < 18:
        return None

    x = round(sum(p[0] for p in points) / len(points))
    y = round(sum(p[1] for p in points) / len(points))
    return speed, x, y


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: find_match_speed.py SCREENSHOT.png')
    try:
        result = find_match_speed(Path(sys.argv[1]))
    except Exception as exc:
        print(f'MATCH_SPEED_DETECT_ERROR={exc}', file=sys.stderr)
        raise SystemExit(2)
    if result is None:
        raise SystemExit(1)
    print(result[0], result[1], result[2])


if __name__ == '__main__':
    main()
