#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

old = '''open_slot0(){
  local tag="$1"
  clear_log; press_career 3
  wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 30 "$tag-saveslot"
  capture_log "$tag saveslot"; shot "$tag-saveslot"
  clear_log; press_slot0 3
}'''

new = '''open_slot0(){
  local tag="$1" attempt reached=0
  for attempt in 1 2 3; do
    clear_log
    echo "Career press attempt $attempt/3"
    press_career 2
    if wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 6 "$tag-saveslot-attempt-$attempt"; then
      reached=1
      break
    fi
    echo "Career press attempt $attempt did not reach SaveSlot; retrying only because MainMenu remained active"
  done
  [ "$reached" -eq 1 ] || { echo "SaveSlot not reached after 3 controlled Career presses"; return 1; }
  capture_log "$tag saveslot"; shot "$tag-saveslot"
  clear_log; press_slot0 3
}'''

if old not in s:
    raise SystemExit('open_slot0 anchor not found')

p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('Applied Stage3 Career input retry patch: max 3 guarded presses, same verified target')
