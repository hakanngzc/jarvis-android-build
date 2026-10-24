#!/usr/bin/env python3
import sys
from pathlib import Path

from PIL import Image


def _is_career_green(pixel: tuple[int, int, int]) -> bool:
    r, g, b = pixel
    return g >= 85 and (g - r) >= 25 and (g - b) >= 45 and r <= 170


def detect_primary_slot_target(src: Path) -> tuple[int, int, list[tuple[int, int]]]:
    im = Image.open(src).convert('RGB')
    w, h = im.size
    x0, x1 = int(w * 0.03), int(w * 0.82)
    rows: list[int] = []

    # Career slot buttons occupy the middle of the NSS 640x960 logical viewport.
    # Limiting the vertical scan to 28%-68% intentionally excludes the top help
    # button and the Back/Tutorial/Google footer controls.
    for y in range(int(h * 0.28), int(h * 0.68), 2):
        hits = 0
        total = 0
        for x in range(x0, x1, 4):
            total += 1
            if _is_career_green(im.getpixel((x, y))):
                hits += 1
        if hits / max(1, total) >= 0.20:
            rows.append(y)

    if not rows:
        raise ValueError('SaveSlot career-button green rows not detected')

    groups: list[tuple[int, int]] = []
    start = prev = rows[0]
    for y in rows[1:]:
        if y - prev <= 4:
            prev = y
        else:
            groups.append((start, prev))
            start = prev = y
    groups.append((start, prev))

    groups = [g for g in groups if (g[1] - g[0]) >= h * 0.025]
    if len(groups) < 3:
        raise ValueError(f'SaveSlot career-button fingerprint incomplete: {groups}')

    y0, y1 = groups[0]
    x = w // 2
    y = (y0 + y1) // 2
    if not (h * 0.28 <= y <= h * 0.46):
        raise ValueError(f'primary SaveSlot target outside expected upper slot region: {(x, y)} bands={groups}')
    return x, y, groups


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: slot_target_geometry.py SCREENSHOT_PNG TARGET_TXT')
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    try:
        x, y, groups = detect_primary_slot_target(src)
    except Exception as exc:
        raise SystemExit(str(exc))
    dst.write_text(f'{x} {y}\n', encoding='utf-8')
    print('slot0_target', x, y, 'green_bands', groups)


if __name__ == '__main__':
    main()
