#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from find_live_ball import PNG_SIG, decode_png_rgb


def validate_frame(path: Path) -> tuple[bool, str | None]:
    try:
        data = path.read_bytes()
        if not data.startswith(PNG_SIG):
            raise ValueError('not a PNG')
        pos = len(PNG_SIG)
        saw_iend = False
        while pos + 12 <= len(data):
            length = struct.unpack('>I', data[pos:pos + 4])[0]
            end = pos + 12 + length
            if end > len(data):
                raise ValueError('truncated PNG chunk')
            kind = data[pos + 4:pos + 8]
            pos = end
            if kind == b'IEND':
                saw_iend = True
                break
        if not saw_iend:
            raise ValueError('missing IEND')
        decode_png_rgb(path)
    except Exception as exc:
        return False, str(exc)
    return True, None


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: validate_frame_png.py SCREENSHOT.png')
    ok, error = validate_frame(Path(sys.argv[1]))
    if not ok:
        print(f'LIVE_FRAME_INVALID={error}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
