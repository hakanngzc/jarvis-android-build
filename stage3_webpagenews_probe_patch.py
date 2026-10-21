#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')
anchor = 'shot fresh-after-save'
if anchor not in s:
    raise SystemExit('fresh-after-save anchor not found after runtime hotfix')
replacement = '''shot fresh-after-save
adb logcat -d -v brief > "$WORK/webpagenews-probe-final.txt" 2>/dev/null || true
if ! grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/webpagenews-probe-final.txt"; then
  echo 'WebPageNews probe did not finish at GameMenu'
  exit 110
fi
capture_log 'webpagenews -> gamemenu probe complete'
echo 'STAGE3_WEBPAGENEWS_PROBE=PASS'
exit 0'''
p.write_text(s.replace(anchor, replacement, 1), encoding='utf-8')
print('Applied Stage3 WebPageNews post-hotfix verification probe')
