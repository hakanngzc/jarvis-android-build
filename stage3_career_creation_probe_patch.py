#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')
old = '''wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 fresh-gamemenu || true
shot fresh-after-save'''
new = '''# Stock NSS opens webpagenews after StartCareer/save before entering GameMenu.
adb logcat -d -v brief > "$WORK/post-career.txt" 2>/dev/null || true
last_active="$(grep -Ei 'SETTING ACTIVE:|SetActive:' "$WORK/post-career.txt" | tail -1 || true)"
if grep -qi 'webpagenews' <<<"$last_active"; then
  capture_log 'fresh Career -> webpagenews'
  clear_log
  press_footer_ok 3
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 fresh-gamemenu
else
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 fresh-gamemenu
fi
capture_log 'fresh Career creation probe complete'
shot fresh-after-save
echo 'STAGE3_CAREER_CREATION_PROBE=PASS'
exit 0'''
if old not in s:
    raise SystemExit('post-career GameMenu anchor not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('Applied Stage3 fresh Career creation probe patch with stock webpagenews continuation')
