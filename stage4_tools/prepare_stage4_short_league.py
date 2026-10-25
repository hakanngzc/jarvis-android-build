#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = (
    "wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation\n"
    "clear_log; press_footer_ok 2"
)

REPLACEMENT = r'''wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
# Run219 proved scroll-based Hong Kong targeting can land on Serbia because the
# stock picker drag distance is not deterministic on hosted emulators. Use the
# fifth row on the initial stock page instead: run199 captured this exact page
# as Albania, Algeria, Andorra, Angola, Argentina, Armenia. The selection is
# still not trusted until stock GetProspectiveClubs proves nation 9 and a
# non-zero candidate set. No Career/season/fixture/match state is patched.
select_argentina_stock_league(){
  local attempt frame="$WORK/short-league-picker.png" tmp="$WORK/short-league-picker.tmp.png" post="$WORK/short-league-post.png" xy rc x y
  for attempt in 1 2 3; do
    echo "short-league Argentina picker attempt $attempt/3" >> "$FLOW"
    press_logical 320 640 1
    rm -f "$tmp" "$frame"
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if ! python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      echo "short-league Argentina picker frame invalid" >> "$FLOW"
      continue
    fi
    mv -f "$tmp" "$frame"
    cp "$frame" "$OUT/short-league-argentina-list.png"
    xy="$(python3 stage4_tools/find_league_picker.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
    if [ "$rc" -ne 0 ]; then
      echo "short-league Argentina fifth-row detector failed rc=$rc" >> "$FLOW"
      continue
    fi

    read -r x y <<<"$xy"
    echo "short-league rendered Argentina candidate row ${x},${y}" >> "$FLOW"
    clear_log
    adb shell input touchscreen tap "$x" "$y" </dev/null || true
    sleep 2

    rm -f "$tmp" "$post"
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      mv -f "$tmp" "$post"
      cp "$post" "$OUT/short-league-argentina-selected.png"
      if ! python3 stage4_tools/find_league_picker.py "$post" >/dev/null 2>>"$FLOW"; then
        echo "short-league Argentina rendered row accepted" >> "$FLOW"
        return 0
      fi
    fi
    echo "short-league Argentina candidate did not close picker" >> "$FLOW"
  done
  echo "short-league Argentina rendered selection could not be proven" >> "$FLOW"
  return 1
}

continue_after_argentina_stock_league(){
  local attempt evidence size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | tail -1)"
  for attempt in 1 2 3; do
    clear_log
    echo "short-league Argentina profile Next attempt $attempt/3" >> "$FLOW"
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
       && ! grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*9([^0-9]|$)' "$evidence"; then
      echo "short-league Argentina wrong stock nation selected" >> "$FLOW"
      return 1
    fi
    if grep -qE 'List of prospective clubs size:[[:space:]]*0([^0-9]|$)' "$evidence"; then
      echo "short-league Argentina produced zero prospective clubs" >> "$FLOW"
      return 1
    fi
    if grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*9([^0-9]|$)' "$evidence" \
       && grep -qE 'List of prospective clubs size:[[:space:]]*[1-9][0-9]*' "$evidence" \
       && grep -qiE 'LoadDataAndStartTrial|TrialDone|Create Screen:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|SetActive:[[:space:]]*message|CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$evidence"; then
      echo "short-league Argentina nation 9 produced viable prospective clubs" >> "$FLOW"
      echo "short-league Argentina profile Next stock transition accepted" >> "$FLOW"
      return 0
    fi

    fatal_check || return 1
    echo "short-league Argentina profile Next attempt $attempt did not prove bootstrap" >> "$FLOW"
  done
  shot "short-league-next-timeout"
  echo "short-league Argentina profile Next timed out" >> "$FLOW"
  return 1
}

select_argentina_stock_league || exit 219
continue_after_argentina_stock_league || exit 218'''


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
    print(f'Applied stock-UI Argentina natural-season selection: {dst}')


if __name__ == '__main__':
    main()
