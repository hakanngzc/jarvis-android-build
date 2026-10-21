#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ENTRY = 'assets/monkey/Tweaks/TweakValues.txt'
OLD = b'Var:(DebugEnabled,Debug Buttons Enabled,0,1)'
NEW = b'Var:(DebugEnabled,Debug Buttons Enabled,1,1)'


def patch(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src, 'r') as zin:
        try:
            data = zin.read(ENTRY)
        except KeyError as exc:
            raise SystemExit(f'missing {ENTRY}; refusing blind debug patch') from exc
        if data.count(OLD) != 1:
            raise SystemExit(f'expected exactly one DebugEnabled default, found {data.count(OLD)}')

        patched = data.replace(OLD, NEW, 1)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.apk', dir=dst.parent) as tf:
            tmp = Path(tf.name)
        try:
            with zipfile.ZipFile(tmp, 'w') as zout:
                for info in zin.infolist():
                    payload = patched if info.filename == ENTRY else zin.read(info.filename)
                    # Reuse the original ZipInfo so method, timestamp, flags and attrs stay intact.
                    zout.writestr(info, payload)
            shutil.move(tmp, dst)
        finally:
            tmp.unlink(missing_ok=True)

    with zipfile.ZipFile(dst, 'r') as check:
        out = check.read(ENTRY)
        if out.count(NEW) != 1 or OLD in out:
            raise SystemExit('DebugEnabled patch postcondition failed')


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit('usage: patch_debug_enabled_test.py INPUT_APK OUTPUT_APK')
    src, dst = map(Path, argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    patch(src, dst)
    print('STAGE3_DEBUG_ENABLED_TEST_PATCH=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
