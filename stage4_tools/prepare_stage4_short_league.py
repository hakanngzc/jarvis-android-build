#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = (
    "wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation\n"
    "clear_log; press_footer_ok 2"
)

REPLACEMENT = r'''wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
# Use the first row on the initial stock page: runtime captures prove this is
# Albania. Runs 202 and 216 further prove stock GetProspectiveClubs reports
# nation id 2 with a non-zero candidate set and reaches real natural matches.
# Keep the source-defined selector centre (332,672) and bounded render polling
# learned from the later Argentina route so the picker is never driven blindly.
# No Career/season/fixture/match state is patched.
select_albania_stock_league(){
  local attempt detect_attempt select_attempt modal_open frame="$WORK/short-league-picker.png" tmp="$WORK/short-league-picker.tmp.png" post="$WORK/short-league-post.png" xy rc x y
  for attempt in 1 2 3; do
    echo "short-league Albania picker open attempt $attempt/3" >> "$FLOW"
    # choosenation.uis source-defined pressable area is logical x=51..613,
    # y=636..708. Use the safe centre rather than a rendered edge coordinate.
    press_logical 332 672 1
    modal_open=0

    # Never re-press the selector while the modal may still be rendering.
    for detect_attempt in 1 2 3 4; do
      rm -f "$tmp" "$frame"
      timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
      if ! python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
        echo "short-league Albania modal frame invalid detect $detect_attempt/4" >> "$FLOW"
        sleep 1
        continue
      fi
      mv -f "$tmp" "$frame"
      cp "$frame" "$OUT/short-league-albania-list.png"
      xy="$(python3 stage4_tools/find_league_picker.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
      if [ "$rc" -eq 0 ]; then
        modal_open=1
        echo "short-league Albania modal ready detect $detect_attempt/4" >> "$FLOW"
        break
      fi
      echo "short-league Albania modal not ready rc=$rc detect $detect_attempt/4" >> "$FLOW"
      sleep 1
    done
    [ "$modal_open" -eq 1 ] || continue

    read -r x y <<<"$xy"
    echo "short-league rendered Albania candidate row ${x},${y}" >> "$FLOW"
    for select_attempt in 1 2 3; do
      clear_log
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      sleep 2

      rm -f "$tmp" "$post"
      timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
      if ! python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
        echo "short-league Albania post-select frame invalid attempt $select_attempt/3" >> "$FLOW"
        sleep 1
        continue
      fi
      mv -f "$tmp" "$post"
      cp "$post" "$OUT/short-league-albania-selected.png"
      if ! python3 stage4_tools/find_league_picker.py "$post" >/dev/null 2>>"$FLOW"; then
        echo "short-league Albania rendered row accepted" >> "$FLOW"
        return 0
      fi
      echo "short-league Albania row tap remained on modal attempt $select_attempt/3" >> "$FLOW"
      sleep 1
    done

    echo "short-league Albania modal remained open after row taps" >> "$FLOW"
    return 1
  done
  echo "short-league Albania rendered selection could not be proven" >> "$FLOW"
  return 1
}

continue_after_albania_stock_league(){
  local attempt evidence size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | tail -1)"
  for attempt in 1 2 3; do
    clear_log
    echo "short-league Albania profile Next attempt $attempt/3" >> "$FLOW"
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
       && ! grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*2([^0-9]|$)' "$evidence"; then
      echo "short-league Albania wrong stock nation selected" >> "$FLOW"
      return 1
    fi
    if grep -qE 'List of prospective clubs size:[[:space:]]*0([^0-9]|$)' "$evidence"; then
      echo "short-league Albania produced zero prospective clubs" >> "$FLOW"
      return 1
    fi
    if grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*2([^0-9]|$)' "$evidence" \
       && grep -qE 'List of prospective clubs size:[[:space:]]*[1-9][0-9]*' "$evidence" \
       && grep -qiE 'LoadDataAndStartTrial|TrialDone|Create Screen:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|SetActive:[[:space:]]*message|CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$evidence"; then
      echo "short-league Albania nation 2 produced viable prospective clubs" >> "$FLOW"
      echo "short-league Albania profile Next stock transition accepted" >> "$FLOW"
      return 0
    fi

    fatal_check || return 1
    echo "short-league Albania profile Next attempt $attempt did not prove bootstrap" >> "$FLOW"
  done
  shot "short-league-next-timeout"
  echo "short-league Albania profile Next timed out" >> "$FLOW"
  return 1
}

select_albania_stock_league || exit 219
continue_after_albania_stock_league || exit 218'''


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
    print(f'Applied source-centred stock-UI Albania natural-season selection: {dst}')


if __name__ == '__main__':
    main()
