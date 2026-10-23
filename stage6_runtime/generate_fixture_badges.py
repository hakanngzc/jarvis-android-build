#!/usr/bin/env python3
import sys
from pathlib import Path
from PIL import Image, ImageDraw

SIZE = (192, 192)


def _shield_mask():
    m = Image.new('L', SIZE, 0)
    d = ImageDraw.Draw(m)
    d.polygon([(24,18),(168,18),(168,112),(96,176),(24,112)], fill=255)
    return m


def _badge_3141():
    img = Image.new('RGBA', SIZE, (0,0,0,0))
    mask = _shield_mask()
    fill = Image.new('RGBA', SIZE, (245,245,235,255))
    d = ImageDraw.Draw(fill)
    for x in range(36, 168, 32):
        d.rectangle((x,18,x+15,140), fill=(25,31,39,255))
    img.paste(fill, (0,0), mask)
    d = ImageDraw.Draw(img)
    d.ellipse((66,58,126,118), outline=(25,31,39,255), width=8)
    d.line((75,88,117,88), fill=(25,31,39,255), width=8)
    return img


def _badge_3163():
    img = Image.new('RGBA', SIZE, (0,0,0,0))
    mask = _shield_mask()
    fill = Image.new('RGBA', SIZE, (205,36,45,255))
    d = ImageDraw.Draw(fill)
    d.polygon([(24,18),(94,18),(168,112),(168,18)], fill=(236,186,36,255))
    d.polygon([(24,112),(96,176),(96,92),(24,18)], fill=(236,186,36,255))
    img.paste(fill, (0,0), mask)
    d = ImageDraw.Draw(img)
    d.rectangle((70,60,122,112), outline=(255,255,255,255), width=8)
    d.line((70,86,122,86), fill=(255,255,255,255), width=8)
    return img


def generate(out_dir: Path):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = {}
    for club_id, image in ((3141,_badge_3141()), (3163,_badge_3163())):
        path = out_dir / f'{club_id}.png'
        image.save(path, optimize=False)
        result[club_id] = path
    return result


def main():
    if len(sys.argv) != 2:
        raise SystemExit(f'usage: {sys.argv[0]} OUT_DIR')
    paths = generate(Path(sys.argv[1]))
    for club_id, path in sorted(paths.items()):
        print(f'fixture_badge_{club_id}={path}')
    print('STAGE6_FIXTURE_BADGES=PASS')


if __name__ == '__main__':
    main()
