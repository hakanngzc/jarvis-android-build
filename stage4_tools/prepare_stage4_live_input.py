#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

DRIVER = r'''drive_live_chance(){
  local cycle="$1" elapsed="$2" frame="$WORK/live-chance.png" xy rc x y target_x target_y direction
  adb exec-out screencap -p > "$frame" 2>/dev/null || true
  xy="$(python3 stage4_tools/find_live_ball.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "cycle $cycle passive live phase @${elapsed}s: no active green ball" >> "$FLOW"
    sleep 2
    return 0
  fi
  if [ "$rc" -ne 0 ]; then
    echo "cycle $cycle live-ball detector failed rc=$rc @${elapsed}s" >> "$FLOW"
    return 1
  fi
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
  echo "cycle $cycle live ball ${x},${y} -> ${target_x},${target_y} @${elapsed}s" >> "$FLOW"
  adb shell input touchscreen swipe "$x" "$y" "$target_x" "$target_y" 420 </dev/null || true
  sleep 3
}
'''

OLD = '''    # Real live-match interaction only: ordinary touchscreen swipes/taps. No
    # match engine method is patched and no hidden simulate/debug branch is used.
    swipe_logical 320 700 320 250 420; sleep 1
    swipe_logical 260 690 460 280 380; sleep 1
    swipe_logical 380 690 180 280 380; sleep 1
    press_logical 320 600 1'''

NEW = '''    # Real live-match interaction only. Read the rendered active-ball marker
    # and perform an ordinary touchscreen swipe starting on that ball. No match
    # engine method, simulate/debug branch or Career/season state is patched.
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
    print(f'Applied rendered-ball-driven natural live-match input: {dst}')


if __name__ == '__main__':
    main()
