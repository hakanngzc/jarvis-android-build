#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

DRIVER = r'''drive_live_chance(){
  local cycle="$1" elapsed="$2" frame="$WORK/live-chance.png" xy rc x y target_x target_y direction kick_xy kick_rc
  adb exec-out screencap -p > "$frame" 2>/dev/null || true

  # Phase A: NSS can first render the small dark-green active-ball marker.
  xy="$(python3 stage4_tools/find_live_ball.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
  if [ "$rc" -eq 0 ]; then
    read -r x y <<<"$xy"
    : "${LIVE_INPUT_SEQ:=0}"
    LIVE_INPUT_SEQ=$((LIVE_INPUT_SEQ + 1))
    direction=$((LIVE_INPUT_SEQ % 3))
    case "$direction" in
      1) target_x=540 ;;
      2) target_x=180 ;;
      *) target_x=900 ;;
    esac
    target_y=$((y - 500))
    [ "$target_y" -ge 180 ] || target_y=180
    [ "$target_y" -le 1750 ] || target_y=1750
    echo "cycle $cycle live marker ${x},${y} -> ${target_x},${target_y} @${elapsed}s" >> "$FLOW"
    adb shell input touchscreen swipe "$x" "$y" "$target_x" "$target_y" 420 </dev/null || true
    sleep 3
    return 0
  fi
  if [ "$rc" -ne 1 ]; then
    echo "cycle $cycle live-marker detector failed rc=$rc @${elapsed}s" >> "$FLOW"
    return 1
  fi

  # Phase B: after that marker interaction, stock NSS can enter the actual
  # kick/pass minigame where a huge white/black football is rendered in the
  # lower-middle pitch. Detect that rendered ball and flick it upward. Any
  # ordinary in-game kick (successful or not) is enough to let the natural
  # match state continue; no match engine or simulate/debug method is touched.
  kick_xy="$(python3 stage4_tools/find_kick_ball.py "$frame" 2>>"$FLOW")" && kick_rc=0 || kick_rc=$?
  if [ "$kick_rc" -eq 0 ]; then
    read -r x y <<<"$kick_xy"
    : "${LIVE_INPUT_SEQ:=0}"
    LIVE_INPUT_SEQ=$((LIVE_INPUT_SEQ + 1))
    direction=$((LIVE_INPUT_SEQ % 3))
    case "$direction" in
      1) target_x=$((x + 80)) ;;
      2) target_x=$((x - 80)) ;;
      *) target_x="$x" ;;
    esac
    [ "$target_x" -ge 120 ] || target_x=120
    [ "$target_x" -le 960 ] || target_x=960
    target_y=$((y - 650))
    [ "$target_y" -ge 220 ] || target_y=220
    echo "cycle $cycle kick ball ${x},${y} -> ${target_x},${target_y} @${elapsed}s" >> "$FLOW"
    adb shell input touchscreen swipe "$x" "$y" "$target_x" "$target_y" 420 </dev/null || true
    sleep 3
    return 0
  fi
  if [ "$kick_rc" -ne 1 ]; then
    echo "cycle $cycle kick-ball detector failed rc=$kick_rc @${elapsed}s" >> "$FLOW"
    return 1
  fi

  echo "cycle $cycle passive live phase @${elapsed}s: no active marker/kick ball" >> "$FLOW"
  sleep 2
  return 0
}
'''

OLD = '''    # Real live-match interaction only: ordinary touchscreen swipes/taps. No
    # match engine method is patched and no hidden simulate/debug branch is used.
    swipe_logical 320 700 320 250 420; sleep 1
    swipe_logical 260 690 460 280 380; sleep 1
    swipe_logical 380 690 180 280 380; sleep 1
    press_logical 320 600 1'''

NEW = '''    # Real live-match interaction only. Detect whichever stock rendered input
    # phase is active (green marker or large kick ball) and perform an ordinary
    # touchscreen swipe. No match engine, simulate/debug branch or season state
    # is patched.
    drive_live_chance "$cycle" "$elapsed"'''


def harden(text: str) -> str:
    if 'drive_live_chance(){' not in text:
        anchor = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }\n'
        if text.count(anchor) != 1:
            raise SystemExit(f'expected one shot helper anchor, found {text.count(anchor)}')
        text = text.replace(anchor, anchor + DRIVER + '\n', 1)
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f'expected one fixed live-input block, found {count}')
    return text.replace(OLD, NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_live_input.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied two-phase rendered-ball natural live-match input: {dst}')


if __name__ == '__main__':
    main()
