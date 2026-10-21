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
  local tag="$1" attempt reached=0 fatal_rc=0 pre_state state
  pre_state="$(current_state 2>/dev/null || echo unknown)"
  if [ "$pre_state" != mainmenu ]; then
    echo "Career input refused: expected mainmenu before first press, state=$pre_state"
    return 1
  fi
  for attempt in 1 2 3; do
    clear_log
    echo "Career press attempt $attempt/3"
    press_career 2
    if wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 6 "$tag-saveslot-attempt-$attempt"; then
      reached=1
      break
    fi
    # wait_log also returns failure when fatal_check fires. Never repeat an input
    # after a real NSS fatal/ANR; diagnose/abort instead of turning it into a
    # misleading SaveSlot timeout loop.
    if ! fatal_check; then
      fatal_rc=1
      echo "NSS fatal detected; aborting Career retry after attempt $attempt"
      return 1
    fi
    state="$(current_state 2>/dev/null || echo unknown)"
    if [ "$state" != unknown ] && [ "$state" != mainmenu ]; then
      echo "Career retry refused: state moved away from mainmenu to $state"
      return 1
    fi
    echo "Career press attempt $attempt did not reach SaveSlot; retrying only because MainMenu remained active"
  done
  [ "$fatal_rc" -eq 0 ] || return 1
  [ "$reached" -eq 1 ] || { echo "SaveSlot not reached after 3 controlled Career presses"; return 1; }
  capture_log "$tag saveslot"; shot "$tag-saveslot"
  clear_log; press_slot0 3
}'''

if old not in s:
    raise SystemExit('open_slot0 anchor not found')

p.write_text(s.replace(old, new, 1), encoding='utf-8')
print('Applied Stage3 Career input retry patch: max 3 guarded presses, fatal-abort, mainmenu precondition')
