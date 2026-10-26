#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

STATE_OLD = '''  case "$line" in
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;; *contract*) echo contract;; *webpage*) echo webpage;; *startransition*) echo startransition;; *skills*) echo skills;; *relationships*) echo relationships;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;; *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;; *) echo unknown;;
  esac
}'''

STATE_NEW = '''  case "$line" in
    *fake-interstitial*) echo fakeinterstitial;; *buxoverlay*) echo buxoverlay;; *purchaseanim*) echo purchaseanim;; *information*) echo information;; *casino*) echo casino;; *dilemma*) echo dilemma;; *splashmessage*) echo splashmessage;;
    *seasonreview*) echo seasonreview;; *playeroftheyear*) echo playeroftheyear;; *desiredtransfer*) echo desiredtransfer;;
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;; *contract*) echo contract;; *webpage*) echo webpage;; *startransition*) echo startransition;; *skills*) echo skills;; *relationships*) echo relationships;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;; *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;; *) echo unknown;;
  esac
}

capture_stage4_event_frame(){
  local final="$1" tmp attempt
  tmp="${final}.tmp"
  rm -f "$tmp" "$final"
  for attempt in 1 2 3; do
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      mv -f "$tmp" "$final"
      return 0
    fi
    rm -f "$tmp"
    sleep 1
  done
  return 1
}

dismiss_stage4_fake_interstitial(){
  echo "stock fake-interstitial -> Android Back" >> "$FLOW"
  adb shell input keyevent 4 </dev/null || true
  sleep 2
}

dismiss_stage4_bux_overlay(){
  local size w h x y
  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | tail -1 | sed -n 's/.*: \([0-9][0-9]*\)x\([0-9][0-9]*\).*/\1 \2/p')"
  read -r w h <<<"$size"
  if [[ "${w:-}" =~ ^[0-9]+$ && "${h:-}" =~ ^[0-9]+$ ]]; then
    x=$((w * 915 / 1000))
    y=$((h * 77 / 1000))
  else
    x=988; y=175
  fi
  echo "stock BuxOverlay visible X -> ${x},${y}" >> "$FLOW"
  adb shell input touchscreen tap "$x" "$y" </dev/null || true
  sleep 2
}

resolve_stage4_dilemma(){
  local attempt frame="$WORK/dilemma-event.png" after="$WORK/dilemma-event-after.png" xy rc x y state
  for attempt in 1 2 3 4; do
    capture_stage4_event_frame "$frame" || { echo "dilemma frame capture failed attempt $attempt/4" >> "$FLOW"; continue; }
    xy="$(python3 stage4_tools/find_dilemma_choice.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
    if [ "$rc" -eq 0 ]; then
      read -r x y <<<"$xy"
      cp "$frame" "$OUT/dilemma-choice-visible.png" 2>/dev/null || true
      clear_log
      echo "stock dilemma upper choice ${x},${y} attempt $attempt/4" >> "$FLOW"
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      sleep 2
      capture_stage4_event_frame "$after" || continue
      if ! python3 stage4_tools/find_dilemma_choice.py "$after" >/dev/null 2>>"$FLOW"; then
        cp "$after" "$OUT/dilemma-choice-accepted.png" 2>/dev/null || true
        echo "stock dilemma choice accepted" >> "$FLOW"
        state="$(latest_state)"
        if [ "$state" = splashmessage ] || [ "$state" = message ]; then
          press_message_accept 2
        fi
        return 0
      fi
      echo "dilemma choice still visible after attempt $attempt" >> "$FLOW"
    elif [ "$rc" -eq 1 ]; then
      echo "dilemma no longer visible; outer navigation will resolve current stock screen" >> "$FLOW"
      return 0
    else
      echo "dilemma detector failed rc=$rc attempt $attempt" >> "$FLOW"
    fi
  done
  echo "stock dilemma could not be resolved after bounded attempts" >> "$FLOW"
  return 1
}'''

NAV_OLD = '''    case "$state" in
      message|webpage|startransition) press_message_accept 2;;
      contract) press_footer_ok 2;;
      *) press_play 2;;
    esac'''

NAV_NEW = '''    case "$state" in
      fakeinterstitial) dismiss_stage4_fake_interstitial || return 1;;
      buxoverlay) dismiss_stage4_bux_overlay || return 1; state=gamemenu;;
      purchaseanim) press_message_accept 1; state=information;;
      information) press_logical 320 910 2;;
      skills) adb shell input keyevent 4 </dev/null || true; sleep 2;;
      casino) press_logical 85 898 2;;
      desiredtransfer) press_logical 85 898 2;;
      dilemma|splashmessage) resolve_stage4_dilemma || return 1;;
      webpage) press_footer_ok 2;;
      message|startransition) press_message_accept 2;;
      contract) press_footer_ok 2;;
      relationships) press_logical 85 898 2;;
      seasonreview|playeroftheyear) press_play 2;;
      *) press_play 2;;
    esac'''

POST_OLD = '''    case "$state" in message|webpage|startransition) press_message_accept 2;; contract) press_footer_ok 2;; *) press_play 2;; esac'''
POST_NEW = '''    case "$state" in fakeinterstitial) dismiss_stage4_fake_interstitial || return 1;; buxoverlay) dismiss_stage4_bux_overlay || return 1; state=gamemenu;; purchaseanim) press_message_accept 1; state=information;; information) press_logical 320 910 2;; skills) adb shell input keyevent 4 </dev/null || true; sleep 2;; casino) press_logical 85 898 2;; desiredtransfer) press_logical 85 898 2;; dilemma|splashmessage) resolve_stage4_dilemma || return 1;; webpage) press_footer_ok 2;; message|startransition) press_message_accept 2;; contract) press_footer_ok 2;; relationships) press_logical 85 898 2;; seasonreview|playeroftheyear) press_play 2;; *) press_play 2;; esac'''

NAV_TRANSITION_OLD = '''    sleep 1
    state="$(latest_state)"
    capture_log "navigate step $step -> $state"
    [ "$state" = match ] && return 0
    [ "$state" = unknown ] && { press_footer_ok 1; state="$(latest_state)"; }'''

NAV_TRANSITION_NEW = '''    sleep 1
    next_state="$(latest_state)"
    if [ "$next_state" = unknown ]; then
      echo "navigate step $step no published transition; retaining $state" >> "$FLOW"
      sleep 1
    else
      state="$next_state"
    fi
    capture_log "navigate step $step -> $state"
    [ "$state" = match ] && return 0'''

POST_TRANSITION_OLD = '''    state="$(latest_state)"; capture_log "cycle $cycle postmatch -> $state"
    [ "$state" = unknown ] && { press_footer_ok 1; state="$(latest_state)"; }'''

POST_TRANSITION_NEW = '''    next_state="$(latest_state)"
    if [ "$next_state" = unknown ]; then
      echo "cycle $cycle postmatch no published transition; retaining $state" >> "$FLOW"
      sleep 1
    else
      state="$next_state"
    fi
    capture_log "cycle $cycle postmatch -> $state"'''


def harden(text: str) -> str:
    if text.count(STATE_OLD) != 1:
        raise SystemExit(f'expected one latest_state block, found {text.count(STATE_OLD)}')
    text = text.replace(STATE_OLD, STATE_NEW, 1)
    if text.count(NAV_OLD) != 1:
        raise SystemExit(f'expected one navigate case, found {text.count(NAV_OLD)}')
    text = text.replace(NAV_OLD, NAV_NEW, 1)
    if text.count(POST_OLD) != 1:
        raise SystemExit(f'expected one postmatch case, found {text.count(POST_OLD)}')
    text = text.replace(POST_OLD, POST_NEW, 1)
    if text.count(NAV_TRANSITION_OLD) != 1:
        raise SystemExit(f'expected one navigate transition block, found {text.count(NAV_TRANSITION_OLD)}')
    text = text.replace(NAV_TRANSITION_OLD, NAV_TRANSITION_NEW, 1)
    if text.count(POST_TRANSITION_OLD) != 1:
        raise SystemExit(f'expected one postmatch transition block, found {text.count(POST_TRANSITION_OLD)}')
    text = text.replace(POST_TRANSITION_OLD, POST_TRANSITION_NEW, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_event_navigation.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied stock event navigation with retained verified state: {dst}')


if __name__ == '__main__':
    main()
