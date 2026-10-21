#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

marker = 'Stage3 stock AdMob interstitial overlay'
anchor = '''current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
'''
old_block = '''  # Stage3 stock AdMob interstitial overlay: it sits above the already-active GameMenu.
  # Detect the top Activity before using stale/cleared Monkey screen logs.
  local activity
  activity="$(timeout 5 adb shell dumpsys activity activities 2>/dev/null || true)"
  if grep -q 'com.newstargames.newstarsoccer/com.google.android.gms.ads.AdActivity' <<<"$activity"; then
    echo ad
    return
  fi
'''
new_block = '''  # Stage3 stock AdMob interstitial overlay: it sits above the already-active GameMenu.
  # Only the resumed/top activity is authoritative. Historical ActivityRecord entries
  # may retain an old AdActivity after MonkeyGame has already resumed.
  local activity resumed
  activity="$(timeout 5 adb shell dumpsys activity activities 2>/dev/null || true)"
  resumed="$(grep -E 'mResumedActivity:|topResumedActivity=|ResumedActivity:' <<<"$activity" | head -n 3 || true)"
  if grep -q 'com.newstargames.newstarsoccer/com.google.android.gms.ads.AdActivity' <<<"$resumed"; then
    echo ad
    return
  fi
'''

if old_block in s:
    s = s.replace(old_block, new_block, 1)
elif marker not in s:
    if anchor not in s:
        raise SystemExit('current_state anchor not found; refusing blind ad-state patch')
    s = s.replace(anchor, anchor + new_block, 1)
elif 'local activity resumed' not in s:
    raise SystemExit('unknown existing AdMob state block; refusing blind migration')

if marker not in s or 'local activity resumed' not in s or 'echo ad' not in s:
    raise SystemExit('ad-state patch postcondition failed')

p.write_text(s, encoding='utf-8')
print('STAGE3_AD_OVERLAY_STATE_PATCH=PASS')
