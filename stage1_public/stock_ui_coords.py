#!/usr/bin/env python3
import re
import subprocess
import sys


def compute_coords(w, h):
    scale = w / 640.0
    B = h / scale
    T = (B - 960.0) * 0.4
    n = (B - 960.0) * 0.7 + 744.0
    logical = {
        'career': (471, 541),
        'slot0': (326, 320 + T), 'slot1': (326, 494 + T), 'slot2': (326, 668 + T),
        'delete0': (567, 319 + T), 'delete1': (567, 493 + T), 'delete2': (567, 667 + T),
        'footer_ok': (553, n + 85), 'message_accept': (477, n + 85),
    }
    return {k: (round(x * scale), round(y * scale)) for k, (x, y) in logical.items()}


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: stock_ui_coords.py OUT')
    s = subprocess.check_output(['adb', 'shell', 'wm', 'size'], text=True)
    m = re.findall(r'(\d+)x(\d+)', s)
    if not m:
        raise SystemExit(s)
    w, h = map(int, m[-1])
    scale = w / 640.0
    B = h / scale
    T = (B - 960.0) * 0.4
    n = (B - 960.0) * 0.7 + 744.0
    coords = compute_coords(w, h)
    with open(sys.argv[1], 'w') as f:
        f.write(f'physical={w}x{h}\nscale={scale:.6f}\nlogical_B={B:.3f}\nlogical_T={T:.3f}\nlogical_n={n:.3f}\n')
        for k, (x, y) in coords.items():
            f.write(f'{k}={x},{y}\n')
    print(open(sys.argv[1]).read())


if __name__ == '__main__':
    main()
