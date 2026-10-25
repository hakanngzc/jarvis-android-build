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
    *dilemma*) echo dilemma;; *splashmessage*) echo splashmessage;;
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
        # Some dilemma outcomes leave a splash-message continuation rather than
        # immediately activating the next Career screen. Use only the ordinary
        # visible message/footer action, then let the outer navigation loop
        # classify the resulting stock screen.
        if [ "$state" = splashmessage ] || [ "$state" = message ]; then
          press_message_accept 2
        fi
        return 0
      fi
      echo "dilemma choice still visible after attempt $attempt" >> "$FLOW"
    elif [ "$rc" -eq 1 ]; then
      # Dilemma visual is already gone but the stock splash-message layer may
      # still be active. Dismiss it with the normal visible message action.
      clear_log
      press_message_accept 2
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
      dilemma|splashmessage) resolve_stage4_dilemma || return 1;;
      message|webpage|startransition) press_message_accept 2;;
      contract) press_footer_ok 2;;
      *) press_play 2;;
    esac'''

POST_OLD = '''    case "$state" in message|webpage|startransition) press_message_accept 2;; contract) press_footer_ok 2;; *) press_play 2;; esac'''
POST_NEW = '''    case "$state" in dilemma|splashmessage) resolve_stage4_dilemma || return 1;; message|webpage|startransition) press_message_accept 2;; contract) press_footer_ok 2;; *) press_play 2;; esac'''


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
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_event_navigation.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied rendered-gated stock Dilemma/SplashMessage navigation: {dst}')


if __name__ == '__main__':
    main()
