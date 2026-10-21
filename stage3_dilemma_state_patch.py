#!/usr/bin/env python3
from pathlib import Path

p = Path('stage3_minimal_gate.sh')
s = p.read_text(encoding='utf-8')

old = '''current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line; line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  case "${line,,}" in
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;;
    *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;; *) echo unknown;;
  esac
}'''

new = '''current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line parent
  line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  if [[ "${line,,}" == *splashmessage* ]]; then
    parent="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | grep -vi 'splashmessage' | tail -1 || true)"
    if [[ "${parent,,}" == *dilemma* ]]; then
      echo dilemma
      return
    fi
  fi
  case "${line,,}" in
    *dilemma*) echo dilemma;; *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;;
    *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;; *) echo unknown;;
  esac
}'''

if new in s:
    print('STAGE3_DILEMMA_STATE_PATCH=ALREADY_APPLIED')
    raise SystemExit(0)
if old not in s:
    raise SystemExit('current_state anchor not found; refusing blind dilemma-state patch')
s = s.replace(old, new, 1)
p.write_text(s, encoding='utf-8')
print('STAGE3_DILEMMA_STATE_PATCH=PASS')
