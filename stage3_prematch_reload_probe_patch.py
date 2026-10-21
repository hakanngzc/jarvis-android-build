#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')
anchor = 'dump_save pre-match'
if anchor not in s:
    raise SystemExit('pre-match save anchor not found')
replacement = '''dump_save pre-match
capture_log 'Stage3 update reload reached GameMenu with readable pre-match save'
test -s "$OUT/pre-match-MonkeyGame.xml"
grep -q 'monkeystate' "$OUT/pre-match-MonkeyGame.xml"
echo 'STAGE3_PREMATCH_RELOAD_PROBE=PASS'
exit 0'''
p.write_text(s.replace(anchor, replacement, 1), encoding='utf-8')
print('Applied Stage3 pre-match reload verification probe')
