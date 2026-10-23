#!/usr/bin/env python3
"""Locate the visible Match PLAY control in stock NSS 4.31 without OCR."""
from __future__ import annotations

import sys
from pathlib import Path
from PIL import Image


def is_play_green(rgb: tuple[int, int, int]) -> bool:
    r, g, b = rgb
    return g >= 105 and g >= r * 1.25 and g >= b * 1.20


def pick(path: Path) -> tuple[int, int, int]:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()
    points: list[tuple[int, int]] = []
    # Stock 4.31 API29 portrait render: circular PLAY control is in the
    # lower-right. Restricting the ROI avoids NRG/kit green artwork.
    for y in range(int(h * 0.75), int(h * 0.86), 2):
        for x in range(int(w * 0.80), int(w * 0.98), 2):
            if is_play_green(px[x, y]):
                points.append((x, y))
    if len(points) < 300:
        raise SystemExit(f'Match PLAY visual fingerprint incomplete: green_pixels={len(points)}')
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    if max(xs) - min(xs) < int(w * 0.08) or max(ys) - min(ys) < int(h * 0.02):
        raise SystemExit('Match PLAY green extent too small')
    x = round(sum(xs) / len(xs))
    y = round(sum(ys) / len(ys))
    print(f'match_play_target {x} {y} green_pixels {len(points)}')
    return x, y, len(points)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: pick_match_play.py screenshot.png output.txt')
    x, y, _ = pick(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(f'{x} {y}\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
