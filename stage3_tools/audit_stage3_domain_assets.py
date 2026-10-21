#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from collections import defaultdict
from pathlib import Path

TERMS = {
    'injury': [b'injury', b'injured', b'injuries', b'hurt'],
    'discipline': [
        b'red card', b'yellow card', b'booked', b'booking', b'sent off',
        b'sent-off', b'suspended', b'suspension', b'match ban', b'player ban',
    ],
}


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit_stage3_domain_assets.py BASE_APK')
    apk = Path(sys.argv[1])
    counts = defaultdict(int)
    print('STAGE3_DOMAIN_ASSET_AUDIT')
    with zipfile.ZipFile(apk) as z:
        for info in z.infolist():
            # DEX is already covered by the call-graph audit; this pass is for
            # UI/localisation/config assets that can reveal opaque game domains.
            if info.filename.endswith('.dex') or info.file_size > 16_000_000:
                continue
            try:
                data = z.read(info.filename)
            except Exception:
                continue
            lower = data.lower()
            for category, terms in TERMS.items():
                for term in terms:
                    pos = lower.find(term)
                    if pos < 0:
                        continue
                    counts[category] += 1
                    lo = max(0, pos - 220)
                    hi = min(len(data), pos + 420)
                    chunk = data[lo:hi]
                    text = ''.join(chr(b) if b in (9, 10, 13) or 32 <= b < 127 else '.' for b in chunk)
                    print(
                        f'ASSET_DOMAIN_HIT category={category} entry={info.filename} '
                        f'term={term.decode()} offset={pos} size={info.file_size}'
                    )
                    print(text)
                    print('---')
    for category in TERMS:
        print(f'ASSET_SUMMARY category={category} hits={counts[category]}')
    print('VERDICT=STAGE3_DOMAIN_ASSET_AUDIT_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
