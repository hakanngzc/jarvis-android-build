#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')
old = '''wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 fresh-gamemenu || true
shot fresh-after-save'''
new = '''wait_log 'Create Screen:[[:space:]]*webpagenews|SETTING ACTIVE:[[:space:]]*webpagenews|SetActive:[[:space:]]*webpagenews' 20 fresh-webpagenews
shot fresh-webpagenews
clear_log
# Verified from the API29 Pixel 4 screenshot: green-ring bounds x=795..1071, y=1709..1970.
# Use the measured physical centre of the stock WebPageNews forward button.
echo 'WebPageNews forward target (stock API29 Pixel 4): 933,1840'
press_physical 933 1840 3
wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 30 fresh-gamemenu
capture_log 'webpagenews -> gamemenu probe complete'
shot fresh-after-webpagenews
echo 'STAGE3_WEBPAGENEWS_PROBE=PASS'
exit 0'''
if old not in s:
    raise SystemExit('fresh gamemenu/webpagenews anchor not found')
p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('Applied Stage3 WebPageNews forward-button probe patch')
