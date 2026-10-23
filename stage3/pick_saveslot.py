#!/usr/bin/env python3
"""Pick the first visible NSS SaveSlot 'New Career' button from a screenshot.

This is intentionally visual rather than OCR/text-dependent. NSS 4.31 renders
three wide bright-green New Career bars in the upper/middle portion of the
SaveSlot screen. We group rows with enough green pixels, reject footer controls,
and choose the first slot bar.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def pick(path: Path) -> tuple[int, int, list[tuple[int, int]]]:
    im = Image.open(path).convert('RGB')
    w, h = im.size
    px = im.load()

    row_hits: list[int] = []
    x0, x1 = int(w * 0.03), int(w * 0.97)
    step = max(1, w // 270)
    samples = max(1, (x1 - x0 + step - 1) // step)
    for y in range(int(h * 0.22), int(h * 0.72), 2):
        green = 0
        for x in range(x0, x1, step):
            r, g, b = px[x, y]
            if g >= 105 and g >= r * 1.28 and g >= b * 1.28:
                green += 1
        # Wide button rows cover most of the screen; circular/help/footer
        # controls do not meet this threshold.
        if green / samples >= 0.28:
            row_hits.append(y)

    if not row_hits:
        raise SystemExit('No wide green SaveSlot button rows detected')

    groups: list[tuple[int, int]] = []
    start = prev = row_hits[0]
    for y in row_hits[1:]:
        if y - prev <= 4:
            prev = y
        else:
            if prev - start >= max(20, int(h * 0.025)):
                groups.append((start, prev))
            start = prev = y
    if prev - start >= max(20, int(h * 0.025)):
        groups.append((start, prev))

    # The SaveSlot screen should expose three similarly sized career bars.
    slot_groups = [g for g in groups if int(h * 0.28) <= g[0] <= int(h * 0.68)]
    if len(slot_groups) < 3:
        raise SystemExit(f'Expected at least 3 SaveSlot green bars, found {slot_groups}')

    y0, y1 = slot_groups[0]
    return w // 2, (y0 + y1) // 2, slot_groups[:3]


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: pick_saveslot.py screenshot.png output.txt')
    x, y, groups = pick(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(f'{x} {y}\n', encoding='utf-8')
    print(f'slot0_target {x} {y} bands {groups}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
