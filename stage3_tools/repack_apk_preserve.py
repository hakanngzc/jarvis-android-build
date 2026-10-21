#!/usr/bin/env python3
import sys, zipfile
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: repack_apk_preserve.py INPUT_APK OUTPUT_APK')
src, dst = map(Path, sys.argv[1:])
with zipfile.ZipFile(src, 'r') as zin:
    entries = [(info, zin.read(info.filename)) for info in zin.infolist()]
with zipfile.ZipFile(dst, 'w') as zout:
    for info, data in entries:
        zi = zipfile.ZipInfo(info.filename, info.date_time)
        zi.compress_type = info.compress_type
        zi.comment = info.comment
        zi.extra = info.extra
        zi.internal_attr = info.internal_attr
        zi.external_attr = info.external_attr
        zi.create_system = info.create_system
        zi.flag_bits = info.flag_bits
        zout.writestr(zi, data)
print(f'REPACK_ONLY=PASS entries={len(entries)} output={dst}')
