#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

HELPER = r'''set_fastest_stock_match_speed(){
  local cycle="$1" attempt frame="$WORK/cycle-${cycle}-match-speed.png" result rc speed x y
  for attempt in 1 2 3 4 5 6; do
    if ! capture_valid_live_frame "$frame"; then
      echo "cycle $cycle stock MatchSpeed frame unavailable attempt $attempt/6" >> "$FLOW"
      sleep 1
      continue
    fi

    result="$(python3 stage4_tools/find_match_speed.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
    if [ "$rc" -eq 1 ]; then
      echo "cycle $cycle stock MatchSpeed icon not visible in current rendered phase" >> "$FLOW"
      return 1  # defer: stock speed icon is not visible in this rendered phase
    fi
    if [ "$rc" -ne 0 ]; then
      echo "cycle $cycle stock MatchSpeed detector failed rc=$rc" >> "$FLOW"
      return 2  # hard detector failure
    fi

    read -r speed x y <<<"$result"
    echo "cycle $cycle stock MatchSpeed=$speed at ${x},${y} attempt $attempt/6" >> "$FLOW"
    if [ "$speed" = 350 ]; then
      cp "$frame" "$OUT/cycle-${cycle}-match-speed-350.png" 2>/dev/null || true
      echo "cycle $cycle stock MatchSpeed=350 verified" >> "$FLOW"
      return 0
    fi

    # Real stock UI only: match.uis declares Click(match.btn_Time) at the
    # rendered speed icon. We tap the detected icon itself and then re-render;
    # no match clock, state field, simulation branch or season data is patched.
    adb shell input touchscreen tap "$x" "$y" </dev/null || true
    sleep 1
  done

  echo "cycle $cycle could not visually verify stock MatchSpeed=350" >> "$FLOW"
  return 1
}

'''

DRIVER_ANCHOR = 'drive_live_chance(){\n'
STATE_ANCHOR = '''  : "${LIVE_EVENT_COUNT:=0}"
  : "${LIVE_LAST_PROBE_EPOCH:=0}"

  # Each natural_match_cycle clears logcat immediately before stock Match Play,'''
STATE_REPLACEMENT = '''  : "${LIVE_EVENT_COUNT:=0}"
  : "${LIVE_LAST_PROBE_EPOCH:=0}"
  : "${LIVE_SPEED_CYCLE:=-1}"
  local speed_rc

  # Set the fastest speed only through the visible stock TimeButton and prove
  # the red 350-state from a fresh rendered frame. Once per natural match.
  # If a live chance is already active, that stock control is intentionally
  # hidden; defer the speed change and keep driving the natural chance instead.
  if [ "$LIVE_SPEED_CYCLE" != "$cycle" ]; then
    if set_fastest_stock_match_speed "$cycle"; then
      LIVE_SPEED_CYCLE="$cycle"
    else
      speed_rc=$?
      if [ "$speed_rc" -ne 1 ]; then
        return "$speed_rc"
      fi
      echo "cycle $cycle MatchSpeed unavailable in current live phase; deferring while live input continues" >> "$FLOW"
    fi
  fi

  # Each natural_match_cycle clears logcat immediately before stock Match Play,'''


def harden(text: str) -> str:
    if 'set_fastest_stock_match_speed(){' in text:
        return text
    if text.count(DRIVER_ANCHOR) != 1:
        raise SystemExit(f'expected one live driver anchor, found {text.count(DRIVER_ANCHOR)}')
    text = text.replace(DRIVER_ANCHOR, HELPER + DRIVER_ANCHOR, 1)
    if text.count(STATE_ANCHOR) != 1:
        raise SystemExit(f'expected one live state anchor, found {text.count(STATE_ANCHOR)}')
    text = text.replace(STATE_ANCHOR, STATE_REPLACEMENT, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_match_speed.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied rendered-verified stock MatchSpeed=350 UI driver: {dst}')


if __name__ == '__main__':
    main()
