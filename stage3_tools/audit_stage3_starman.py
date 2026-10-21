#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dex_inspect import Dex

STAR_RE = re.compile(r'starman|star.?man', re.I)


def inspect_dex(path: Path, label: str):
    d = Dex(path)
    lines = []
    classes = sorted({t for t in d.types if STAR_RE.search(t)})
    for cls in classes:
        methods = d.class_methods(cls) or []
        lines.append(f'STARMAN_CLASS dex={label} class={cls} method_count={len(methods)}')
        for kind, mid, method, access, code in methods:
            lines.append(f'  METHOD name={method[1]} id={mid} kind={kind} access=0x{access:x} code=0x{code:x}')
            if code and re.search(r'Button|Play|Continue|Hit|Create|SetActive|Call', method[1], re.I):
                _regs, _ins, _outs, _tries, _size, items = d.disasm(code)
                for off, op, args, raw in items:
                    if args or op.startswith(('invoke-', 'sget', 'iget', 'sput', 'iput')):
                        lines.append(f'    {off:05x} {raw:<28} {op:<24} {args}')
    return lines


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit_stage3_starman.py BASE_APK')
    apk = Path(sys.argv[1])
    lines = []
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for name in z.namelist():
            if re.fullmatch(r'classes\d*\.dex', Path(name).name):
                out = Path(td) / Path(name).name
                out.write_bytes(z.read(name))
                lines.extend(inspect_dex(out, Path(name).name))

        for info in z.infolist():
            if info.file_size > 4_000_000 or info.filename.endswith('.dex'):
                continue
            try:
                data = z.read(info.filename)
            except Exception:
                continue
            low = data.lower()
            for needle in (b'starman', b'star man'):
                pos = low.find(needle)
                if pos < 0:
                    continue
                lo = max(0, pos - 900)
                hi = min(len(data), pos + 2200)
                chunk = data[lo:hi]
                text = ''.join(chr(b) if b in (9,10,13) or 32 <= b < 127 else '.' for b in chunk)
                lines.append(f'STARMAN_ASSET entry={info.filename} needle={needle.decode()} offset={pos} size={info.file_size}')
                lines.append(text)
                break

    text = '\n'.join(lines)
    print('STAGE3_STARMAN_AUDIT')
    print(text)
    if 'STARMAN_CLASS' not in text or 'STARMAN_ASSET' not in text:
        raise SystemExit('StarMan class/asset evidence incomplete')
    print('VERDICT=STAGE3_STARMAN_AUDIT_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
