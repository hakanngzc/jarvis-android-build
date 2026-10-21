#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ENTRY = 'assets/monkey/Tweaks/TweakValues.txt'
CATEGORY_RE = re.compile(r'^\s*Category:\(([^)]+)\)', re.I)
END_RE = re.compile(r'^\s*EndCategory\b', re.I)
INTEREST = re.compile(r'match|chance|minute|clock|time|fastforward|player.*boost|goal|penalty|freekick', re.I)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit_stage3_match_tweaks.py BASE_APK')
    apk = Path(sys.argv[1])
    with zipfile.ZipFile(apk) as z:
        text = z.read(ENTRY).decode('utf-8', errors='replace')

    lines = text.splitlines()
    stack: list[str] = []
    hits = 0
    print('STAGE3_MATCH_TWEAK_AUDIT')
    for i, line in enumerate(lines, 1):
        m = CATEGORY_RE.match(line)
        if m:
            stack.append(m.group(1))
        path = '/'.join(stack)
        if INTEREST.search(line) or INTEREST.search(path):
            if line.strip():
                hits += 1
                print(f'{i:05d} category={path or "<root>"} :: {line}')
        if END_RE.match(line) and stack:
            stack.pop()

    print(f'MATCH_TWEAK_HITS={hits}')
    if not hits:
        raise SystemExit('no match/timing/chance tweak evidence found')
    print('VERDICT=STAGE3_MATCH_TWEAK_AUDIT_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
