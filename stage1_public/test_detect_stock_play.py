#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image, ImageDraw

ROOT = Path(__file__).parent
SCRIPT = ROOT / 'detect_stock_play.py'

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    img = Image.new('RGB', (1080, 2280), (25, 45, 70))
    draw = ImageDraw.Draw(img)
    # Real stock main-menu geometry: Play is the first of four green action
    # bands and begins below the obsolete 0.58*h detector cutoff.
    for y0 in (1330, 1482, 1634, 1786):
        draw.rounded_rectangle((540, y0, 1015, y0 + 108), radius=18, fill=(55, 180, 10))
    png = td / 'menu.png'
    out = td / 'target.txt'
    img.save(png)
    p = subprocess.run([sys.executable, str(SCRIPT), str(png), str(out)], text=True, capture_output=True)
    assert p.returncode == 0, (p.stdout, p.stderr)
    x, y = map(int, out.read_text().split())
    assert 540 <= x <= 1015, (x, y)
    assert 1330 <= y <= 1438, (x, y)

print('STOCK_PLAY_DETECTOR_TEST=PASS')
