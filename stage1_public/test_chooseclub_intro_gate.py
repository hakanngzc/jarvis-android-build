#!/usr/bin/env python3
from pathlib import Path

p = Path('stage1_public/runtime_gate_v2.sh')
if not p.exists():
    raise SystemExit('runtime_gate_v2.sh missing; run build_runtime_gate_v2.py first')
s = p.read_text()
start = s.index('create_career(){')
end = s.index('manual_load_slot(){', start)
block = s[start:end]
shot = block.index('shot "$stem-chooseclub"')
first_profile_ok = block.index('press "$OK_X" "$OK_Y" 2', shot)
intro_accept = block.find('accept_message_if_present', shot, first_profile_ok)
assert intro_accept != -1, 'ChooseClub onboarding message is not accepted before stock profile OK flow'
assert block.count('press "$OK_X" "$OK_Y"', shot) >= 2, 'stock two-OK profile flow missing'
print('CHOOSECLUB_INTRO_GATE_TEST=PASS')
