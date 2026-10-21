#!/usr/bin/env python3
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

if len(sys.argv) != 3:
    raise SystemExit('usage: patch_first_run_overlays.py INPUT_APK OUTPUT_APK')

src = Path(sys.argv[1])
dst = Path(sys.argv[2])

ONBOARD = 'assets/monkey/NewGUI/Screens/onboardingmain.uih'
CONSENT = 'assets/monkey/NewGUI/Screens/consent.uih'
ONBOARD_DATA = b'Rect:(0,0,0,0)\n    SetTweak(FirstPlayLocal,FirstPlayIncrement,4)\n'
CONSENT_DATA = b'Macro:(M_Consent_Panel)\nEndM\nMacro:(M_Consent_Panel_ATT)\nEndM\n'
TARGETS = {ONBOARD, CONSENT}

seen: set[str] = set()
with zipfile.ZipFile(src, 'r') as zin, zipfile.ZipFile(dst, 'w', allowZip64=True) as zout:
    for info in zin.infolist():
        data = zin.read(info.filename)
        if info.filename == ONBOARD:
            data = ONBOARD_DATA
            seen.add(ONBOARD)
        elif info.filename == CONSENT:
            data = CONSENT_DATA
            seen.add(CONSENT)
        zout.writestr(info, data)

missing = TARGETS - seen
if missing:
    try:
        dst.unlink()
    except FileNotFoundError:
        pass
    raise SystemExit(f'missing overlay targets: {sorted(missing)}')

print('FIRST_RUN_OVERLAY_PATCH=PASS')
for target in sorted(seen):
    print('replaced', target)
print('changed_entry_count=2')
