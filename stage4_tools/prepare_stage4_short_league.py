#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = (
    "wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation\n"
    "clear_log; press_footer_ok 2"
)

REPLACEMENT = r'''wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
# Experimental fast natural-season route on an isolated branch only. Stock
# choosenation.uis renders six 100-logical-height nation rows inside a
# 600-logical-height scrolling list. Philippines is selectable index 80, so
# thirteen full-page moves (78 rows) put it on the third visible row. The
# selection is accepted ONLY if stock GetProspectiveClubs later reports nation
# ID 149 and a non-zero candidate set. No Career/season/match state is patched.
select_philippines_stock_league(){
  local attempt page frame="$WORK/short-league-picker.png" tmp="$WORK/short-league-picker.tmp.png" post="$WORK/short-league-post.png" xy rc x y
  for attempt in 1 2; do
    echo "short-league Philippines picker attempt $attempt/2" >> "$FLOW"
    press_logical 320 640 1
    rm -f "$tmp" "$frame"
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if ! python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      echo "short-league Philippines picker frame invalid" >> "$FLOW"
      continue
    fi
    mv -f "$tmp" "$frame"

    for page in $(seq 1 13); do
      echo "short-league Philippines page scroll $page/13" >> "$FLOW"
      # Long gesture minimizes fling/inertia so each movement stays close to
      # the stock 600-logical-height page size.
      swipe_logical 320 780 320 180 1600
      sleep 1
    done

    rm -f "$tmp" "$frame"
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if ! python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      echo "short-league Philippines scrolled frame invalid" >> "$FLOW"
      continue
    fi
    mv -f "$tmp" "$frame"
    xy="$(python3 stage4_tools/find_league_picker.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
    if [ "$rc" -eq 0 ]; then
      read -r x y <<<"$xy"
      cp "$frame" "$OUT/short-league-philippines-list.png"
      echo "short-league rendered Philippines row ${x},${y}" >> "$FLOW"
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      sleep 2
      rm -f "$tmp" "$post"
      timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
      if python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
        mv -f "$tmp" "$post"
        if ! python3 stage4_tools/find_league_picker.py "$post" >/dev/null 2>>"$FLOW"; then
          cp "$post" "$OUT/short-league-philippines-selected.png"
          echo "short-league Philippines rendered row accepted" >> "$FLOW"
          return 0
        fi
      fi
      echo "short-league Philippines row did not close picker" >> "$FLOW"
    fi
  done
  echo "short-league Philippines rendered selection could not be proven" >> "$FLOW"
  return 1
}

continue_after_philippines_stock_league(){
  local attempt evidence size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | tail -1)"
  for attempt in 1 2 3; do
    clear_log
    echo "short-league Philippines profile Next attempt $attempt/3" >> "$FLOW"
    if [[ "$size" == *1080x2280* ]]; then
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
    cp "$evidence" "$OUT/short-league-next-${attempt}.txt" 2>/dev/null || true

    if grep -qE 'GetProspectiveClubs for nation Id:' "$evidence" \
       && ! grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*149([^0-9]|$)' "$evidence"; then
      echo "short-league Philippines wrong stock nation selected" >> "$FLOW"
      return 1
    fi
    if grep -qE 'List of prospective clubs size:[[:space:]]*0([^0-9]|$)' "$evidence"; then
      echo "short-league Philippines produced zero prospective clubs" >> "$FLOW"
      return 1
    fi
    if grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*149([^0-9]|$)' "$evidence" \
       && grep -qE 'List of prospective clubs size:[[:space:]]*[1-9][0-9]*' "$evidence" \
       && grep -qiE 'LoadDataAndStartTrial|TrialDone|Create Screen:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|SetActive:[[:space:]]*message|CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$evidence"; then
      echo "short-league Philippines nation 149 produced viable prospective clubs" >> "$FLOW"
      echo "short-league Philippines profile Next stock transition accepted" >> "$FLOW"
      return 0
    fi

    fatal_check || return 1
    echo "short-league Philippines profile Next attempt $attempt did not prove bootstrap" >> "$FLOW"
  done
  shot "short-league-next-timeout"
  echo "short-league Philippines profile Next timed out" >> "$FLOW"
  return 1
}

select_philippines_stock_league || exit 219
continue_after_philippines_stock_league || exit 218'''


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
    print(f'Applied rendered-gated stock-UI Philippines fast-league selection: {dst}')


if __name__ == '__main__':
    main()
