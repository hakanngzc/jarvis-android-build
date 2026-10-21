#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

marker = 'Stage3 StarMan parent state: bottom-message overlays are internal'
case_anchor = '''  case "${line,,}" in
'''
block = '''  # Stage3 StarMan parent state: bottom-message overlays are internal to the
  # StarMan screen. Run 39672454504 observed starman -> bottommessageachievement
  # without a new starman SetActive after dismissing the overlay, so preserve the
  # last non-overlay parent screen exactly like the Dilemma/splashmessage rule.
  if [[ "${line,,}" == *bottommessageachievement* || "${line,,}" == *bottommessagerecord* ]]; then
    parent="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | grep -viE 'bottommessageachievement|bottommessagerecord|splashmessage' | tail -1 || true)"
    if [[ "${parent,,}" == *starman* ]]; then
      echo starman
      return
    fi
  fi
  if [[ "${line,,}" == *starman* ]]; then
    echo starman
    return
  fi
'''

if marker in s:
    print('STAGE3_STARMAN_STATE_PATCH=ALREADY_APPLIED')
    raise SystemExit(0)
if case_anchor not in s:
    raise SystemExit('current_state case anchor not found; refusing blind starman-state patch')

s = s.replace(case_anchor, block + case_anchor, 1)
if marker not in s or 'bottommessageachievement' not in s or 'echo starman' not in s:
    raise SystemExit('starman-state patch postcondition failed')

p.write_text(s, encoding='utf-8')
print('STAGE3_STARMAN_STATE_PATCH=PASS')
