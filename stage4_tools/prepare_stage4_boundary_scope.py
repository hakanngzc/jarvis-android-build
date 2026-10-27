#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

BASE_OLD = '''dump_save natural-baseline; checkpoint natural-baseline
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''
BASE_NEW = '''dump_save natural-baseline; checkpoint natural-baseline
# Only season-transition evidence emitted after the baseline checkpoint counts.
# This excludes NewSeasonSetUp markers that may occur during fresh-Career bootstrap.
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

CHECK_OLD = '''  adb logcat -d -v brief >> "$FLOW" 2>/dev/null || true
  if grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp1' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp2' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp3' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp4' "$FLOW"; then
    SEASON_SEEN=1; break
  fi'''
CHECK_NEW = '''  adb logcat -d -v brief >> "$FLOW" 2>/dev/null || true
  tail -c +$((BASE_FLOW_BYTES + 1)) "$FLOW" > "$WORK/post-baseline-season-flow.log" 2>/dev/null || true
  if grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp1' "$WORK/post-baseline-season-flow.log" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp2' "$WORK/post-baseline-season-flow.log" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp3' "$WORK/post-baseline-season-flow.log" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp4' "$WORK/post-baseline-season-flow.log"; then
    SEASON_SEEN=1; break
  fi'''

NAV_FN_OLD = '''navigate_until_match(){'''
NAV_FN_NEW = '''stage4_live_boundary_seen(){
  local setup_n
  adb logcat -d -v brief > "$WORK/boundary-live.log" 2>/dev/null || true
  for setup_n in 1 2 3 4; do
    grep -q "CallFunc:[[:space:]]*NewSeasonSetUp${setup_n}" "$WORK/boundary-live.log" || return 1
  done
  return 0
}

navigate_until_match(){'''

NAV_CAPTURE_OLD = '''    capture_log "navigate step $step -> $state"
    [ "$state" = match ] && return 0'''
NAV_CAPTURE_NEW = '''    capture_log "navigate step $step -> $state"
    if stage4_live_boundary_seen; then
      STAGE4_BOUNDARY_REACHED=1
      echo "natural season boundary complete; stop before post-rollover Play" >> "$FLOW"
      return 0
    fi
    [ "$state" = match ] && return 0'''

CYCLE_NAV_OLD = '''  navigate_until_match || { shot "cycle-$cycle-no-match"; return 1; }
  shot "cycle-$cycle-match"'''
CYCLE_NAV_NEW = '''  STAGE4_BOUNDARY_REACHED=0
  navigate_until_match || { shot "cycle-$cycle-no-match"; return 1; }
  [ "${STAGE4_BOUNDARY_REACHED:-0}" -eq 1 ] && return 0
  shot "cycle-$cycle-match"'''


def replace_one(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'expected one {label} anchor, found {count}')
    return text.replace(old, new, 1)


def harden(text: str) -> str:
    text = replace_one(text, BASE_OLD, BASE_NEW, 'baseline marker')
    text = replace_one(text, CHECK_OLD, CHECK_NEW, 'season marker check')
    text = replace_one(text, NAV_FN_OLD, NAV_FN_NEW, 'navigation function')
    text = replace_one(text, NAV_CAPTURE_OLD, NAV_CAPTURE_NEW, 'navigation transition')
    text = replace_one(text, CYCLE_NAV_OLD, CYCLE_NAV_NEW, 'cycle navigation')
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_boundary_scope.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied post-baseline season scope with first-rollover stop: {dst}')


if __name__ == '__main__':
    main()
