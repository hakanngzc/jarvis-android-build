#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = (
    "wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation\n"
    "clear_log; press_footer_ok 2"
)

REPLACEMENT = r'''wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
# Natural-season setup optimization only: open the stock rendered league picker
# and select its visible Andorra row. A rendered-frame gate is required because
# hosted-emulator touchscreen taps can occasionally be consumed. No save field,
# season date, fixture, competition state or match/simulate method is patched.
select_andorra_stock_league(){
  local attempt frame="$WORK/short-league-picker.png" tmp="$WORK/short-league-picker.tmp.png" post="$WORK/short-league-post.png" xy rc x y
  for attempt in 1 2 3 4; do
    echo "short-league picker open attempt $attempt/4" >> "$FLOW"
    press_logical 320 640 1
    rm -f "$tmp" "$frame"
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if ! python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      echo "short-league picker frame invalid on attempt $attempt" >> "$FLOW"
      continue
    fi
    mv -f "$tmp" "$frame"
    xy="$(python3 stage4_tools/find_league_picker.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
    if [ "$rc" -eq 0 ]; then
      read -r x y <<<"$xy"
      cp "$frame" "$OUT/short-league-list-open.png"
      echo "short-league rendered Andorra row ${x},${y}" >> "$FLOW"
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      sleep 2
      rm -f "$tmp" "$post"
      timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
      if python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
        mv -f "$tmp" "$post"
        if ! python3 stage4_tools/find_league_picker.py "$post" >/dev/null 2>>"$FLOW"; then
          cp "$post" "$OUT/short-league-andorra-selected.png"
          echo "short-league Andorra stock row accepted" >> "$FLOW"
          return 0
        fi
      fi
      echo "short-league Andorra tap did not close picker; retrying" >> "$FLOW"
    elif [ "$rc" -ne 1 ]; then
      echo "short-league picker detector failed rc=$rc" >> "$FLOW"
    fi
  done
  echo "short-league stock Andorra selection could not be proven" >> "$FLOW"
  return 1
}

continue_after_andorra_stock_league(){
  local attempt evidence size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r')"
  for attempt in 1 2 3; do
    clear_log
    echo "short-league profile Next attempt $attempt/3" >> "$FLOW"
    if [[ "$size" == *1080x2280* ]]; then
      # Run184 proves Andorra selection returns to the same player-profile
      # surface whose stock Next control was already measured at 940,1830.
      if [ "$attempt" = 1 ]; then
        adb shell input touchscreen tap 940 1830 </dev/null || true
      else
        adb shell input touchscreen swipe 940 1830 940 1830 220 </dev/null || true
      fi
      sleep 4
    else
      press_footer_ok 4
    fi

    evidence="$WORK/short-league-next-${attempt}.txt"
    adb logcat -d -v brief > "$evidence" 2>/dev/null || true
    if grep -qiE 'LoadDataAndStartTrial|TrialDone|Create Screen:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|SetActive:[[:space:]]*message|CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$evidence"; then
      cp "$evidence" "$OUT/short-league-next-${attempt}.txt" 2>/dev/null || true
      echo "short-league profile Next stock transition accepted" >> "$FLOW"
      return 0
    fi
    cp "$evidence" "$OUT/short-league-next-${attempt}.txt" 2>/dev/null || true
    fatal_check || return 1
    echo "short-league profile Next attempt $attempt did not advance; retrying" >> "$FLOW"
  done
  shot "short-league-next-timeout"
  echo "short-league profile Next could not reach stock career bootstrap" >> "$FLOW"
  return 1
}

select_andorra_stock_league || exit 219
continue_after_andorra_stock_league || exit 218'''


def harden(text: str) -> str:
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(f'expected one ChooseNation continue anchor, found {count}')
    return text.replace(ANCHOR, REPLACEMENT, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_short_league.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied rendered-gated stock-UI Andorra short-league selection: {dst}')


if __name__ == '__main__':
    main()
