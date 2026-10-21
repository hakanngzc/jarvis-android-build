#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

marker = 'Stage3 stock AdMob interstitial overlay'
if marker not in s:
    anchor = '''current_state(){\n  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true\n'''
    replacement = '''current_state(){\n  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true\n  # Stage3 stock AdMob interstitial overlay: it sits above the already-active GameMenu.\n  # Detect the top Activity before using stale/cleared Monkey screen logs.\n  local activity\n  activity="$(timeout 5 adb shell dumpsys activity activities 2>/dev/null || true)"\n  if grep -q 'com.newstargames.newstarsoccer/com.google.android.gms.ads.AdActivity' <<<"$activity"; then\n    echo ad\n    return\n  fi\n'''
    if anchor not in s:
        raise SystemExit('current_state anchor not found; refusing blind ad-state patch')
    s = s.replace(anchor, replacement, 1)

if marker not in s or 'echo ad' not in s:
    raise SystemExit('ad-state patch postcondition failed')

p.write_text(s, encoding='utf-8')
print('STAGE3_AD_OVERLAY_STATE_PATCH=PASS')
