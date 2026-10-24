#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

PNG_SIG = b'\x89PNG\r\n\x1a\n'


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def decode_png_rgb(path: Path):
    data = path.read_bytes()
    if not data.startswith(PNG_SIG):
        raise ValueError('not a PNG')
    pos = len(PNG_SIG)
    width = height = bit_depth = color_type = None
    payload = bytearray()
    while pos + 12 <= len(data):
        length = struct.unpack('>I', data[pos:pos + 4])[0]
        kind = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if kind == b'IHDR':
            width, height, bit_depth, color_type, _comp, _filter, interlace = struct.unpack('>IIBBBBB', chunk)
            if bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
                raise ValueError(f'unsupported PNG: depth={bit_depth} color={color_type} interlace={interlace}')
        elif kind == b'IDAT':
            payload.extend(chunk)
        elif kind == b'IEND':
            break
    if width is None or height is None:
        raise ValueError('missing IHDR')
    channels = 3 if color_type == 2 else 4
    stride = width * channels
    raw = zlib.decompress(bytes(payload))
    if len(raw) != height * (stride + 1):
        raise ValueError('bad decompressed PNG size')
    rows = []
    prev = bytearray(stride)
    off = 0
    for _ in range(height):
        filter_type = raw[off]
        off += 1
        src = raw[off:off + stride]
        off += stride
        out = bytearray(stride)
        for i, value in enumerate(src):
            a = out[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if filter_type == 0:
                decoded = value
            elif filter_type == 1:
                decoded = (value + a) & 255
            elif filter_type == 2:
                decoded = (value + b) & 255
            elif filter_type == 3:
                decoded = (value + ((a + b) // 2)) & 255
            elif filter_type == 4:
                decoded = (value + _paeth(a, b, c)) & 255
            else:
                raise ValueError(f'unsupported PNG filter {filter_type}')
            out[i] = decoded
        rows.append(bytes(out))
        prev = out
    return width, height, channels, rows


def find_live_ball(path: Path):
    width, height, channels, rows = decode_png_rgb(path)
    points = []
    y0, y1 = int(height * 0.25), int(height * 0.88)
    for y in range(y0, y1):
        row = rows[y]
        for x in range(width):
            i = x * channels
            r, g, b = row[i], row[i + 1], row[i + 2]
            if 18 <= g <= 125 and r <= 16 and b <= 16 and g >= r + 15 and g >= b + 15:
                points.append((x, y))
    if not points:
        return None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    box_w, box_h = maxx - minx + 1, maxy - miny + 1
    if not (25 <= box_w <= 180 and 25 <= box_h <= 180 and len(points) >= 120):
        return None
    return round((minx + maxx) / 2), round((miny + maxy) / 2)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: find_live_ball.py SCREENSHOT.png')
    try:
        hit = find_live_ball(Path(sys.argv[1]))
    except Exception as exc:
        print(f'LIVE_BALL_DETECT_ERROR={exc}', file=sys.stderr)
        raise SystemExit(2)
    if hit is None:
        raise SystemExit(1)
    print(hit[0], hit[1])


if __name__ == '__main__':
    main()
