#!/usr/bin/env python3
from pathlib import Path

p = Path('stage1_public/runtime_gate_v2.sh')
s = p.read_text()

old = '''  shot "$stem-chooseclub"
  # Stock blank-name behavior: first OK supplies default name, second advances.
  press "$OK_X" "$OK_Y" 2
  press "$OK_X" "$OK_Y" 3
'''
new = '''  shot "$stem-chooseclub"
  # Stock creates ChooseClub and immediately overlays the one-time welcome
  # message. Dismiss that layer first; then preserve the stock two-OK profile
  # flow (default blank name, then advance).
  accept_message_if_present
  press "$OK_X" "$OK_Y" 2
  press "$OK_X" "$OK_Y" 3
'''

if s.count(old) != 1:
    raise SystemExit(f'ChooseClub intro patch anchor count={s.count(old)}')
s = s.replace(old, new, 1)
p.write_text(s)

block = s[s.index('create_career(){'):s.index('manual_load_slot(){')]
shot = block.index('shot "$stem-chooseclub"')
first_profile_ok = block.index('press "$OK_X" "$OK_Y" 2', shot)
intro_accept = block.find('accept_message_if_present', shot, first_profile_ok)
if intro_accept == -1:
    raise SystemExit('ChooseClub welcome acceptance missing after patch')
print('CHOOSECLUB_INTRO_PATCH=PASS')
