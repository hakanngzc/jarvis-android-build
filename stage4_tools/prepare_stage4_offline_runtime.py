#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = 'start_game fresh; open_slot0 fresh'

REPLACEMENT = r'''# Keep the Stage4 durability run deterministic and scoped to stock Career /
# match / season behavior. Third-party ad delivery is outside this gate and can
# foreground AdActivity between natural matches, so run the Android guest
# offline. The APK, Career state, fixture state and season methods are untouched.
echo 'Stage4 natural runtime: disabling Android guest external network' >> "$FLOW"
adb shell settings put global airplane_mode_on 1 >/dev/null 2>&1 || true
adb shell am broadcast -a android.intent.action.AIRPLANE_MODE --ez state true >/dev/null 2>&1 || true
adb shell svc wifi disable >/dev/null 2>&1 || true
adb shell svc data disable >/dev/null 2>&1 || true
adb shell ip link set eth0 down >/dev/null 2>&1 || true
{
  echo 'STAGE4_EXTERNAL_NETWORK_DISABLED=1'
  adb shell ip route 2>/dev/null || true
} > "$OUT/network-isolation.txt"
start_game fresh; open_slot0 fresh'''


def harden(text: str) -> str:
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(f'expected one fresh Career bootstrap anchor, found {count}')
    return text.replace(ANCHOR, REPLACEMENT, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_offline_runtime.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied Android-guest offline isolation for natural Stage4 runtime: {dst}')


if __name__ == '__main__':
    main()
