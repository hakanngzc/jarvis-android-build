#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

marker = 'Stage3 dilemma parent state: splashmessage is internal to dilemma'
line_anchor = '''  local line; line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"'''
line_replacement = '''  # Stage3 dilemma parent state: splashmessage is internal to dilemma, not a standalone Message screen.
  local line parent
  line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  if [[ "${line,,}" == *splashmessage* ]]; then
    parent="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | grep -vi 'splashmessage' | tail -1 || true)"
    if [[ "${parent,,}" == *dilemma* ]]; then
      echo dilemma
      return
    fi
  fi'''
case_anchor = '''  case "${line,,}" in
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;;'''
case_replacement = '''  case "${line,,}" in
    *dilemma*) echo dilemma;; *matchstats*) echo matchstats;; *matchreview*) echo matchreview;;'''

if marker in s:
    print('STAGE3_DILEMMA_STATE_PATCH=ALREADY_APPLIED')
    raise SystemExit(0)
if line_anchor not in s:
    raise SystemExit('current_state line anchor not found; refusing blind dilemma-state patch')
if case_anchor not in s:
    raise SystemExit('current_state case anchor not found; refusing blind dilemma-state patch')

s = s.replace(line_anchor, line_replacement, 1)
s = s.replace(case_anchor, case_replacement, 1)

if marker not in s or 'echo dilemma' not in s or 'grep -vi \'splashmessage\'' not in s:
    raise SystemExit('dilemma-state patch postcondition failed')

p.write_text(s, encoding='utf-8')
print('STAGE3_DILEMMA_STATE_PATCH=PASS')
