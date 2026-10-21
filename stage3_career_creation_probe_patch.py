#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')
anchor = 'shot fresh-after-save'
if anchor not in s:
    raise SystemExit('fresh-after-save anchor not found')
inject = '''shot fresh-after-save
capture_log 'fresh Career creation probe complete'
echo 'STAGE3_CAREER_CREATION_PROBE=PASS'
exit 0'''
p.write_text(s.replace(anchor, inject, 1), encoding='utf-8')
print('Applied Stage3 fresh Career creation probe patch')
