#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')
anchor = 'shot fresh-after-save'
if anchor not in s:
    raise SystemExit('fresh-after-save anchor not found after runtime hotfix')
replacement = '''shot fresh-after-save
adb logcat -d -v brief > "$WORK/career-probe-final.txt" 2>/dev/null || true
if ! grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/career-probe-final.txt"; then
  echo 'Fresh Career probe did not finish at GameMenu'
  exit 111
fi
capture_log 'fresh Career save -> webpagenews -> GameMenu complete'
echo 'STAGE3_CAREER_CREATION_PROBE=PASS'
exit 0'''
p.write_text(s.replace(anchor, replacement, 1), encoding='utf-8')
print('Applied Stage3 fresh Career post-hotfix verification probe')
