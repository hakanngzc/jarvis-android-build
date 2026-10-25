#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = (
    "wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation\n"
    "clear_log; press_footer_ok 2"
)

REPLACEMENT = r'''wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
# Run217's stock runtime log gives the authoritative league-bearing selector
# order: Hong Kong is zero-based index 42 among nations with leagues. Seven slow
# 600-logical-height page drags therefore place it on the first visible row.
# Run219 proved that reopening the picker retains its scroll position, so a
# detector retry must never repeat those seven drags or it overshoots to Serbia.
# The selection is not trusted until stock GetProspectiveClubs proves nation 87
# and a non-zero candidate set. No Career/season/fixture/match state is patched.
select_hong_kong_stock_league(){
  local page detect_attempt frame="$WORK/short-league-picker.png" tmp="$WORK/short-league-picker.tmp.png" post="$WORK/short-league-post.png" xy rc x y
  echo "short-league Hong Kong picker open" >> "$FLOW"
  press_logical 320 640 1

  for page in 1 2 3 4 5 6 7; do
    echo "short-league Hong Kong page scroll $page/7" >> "$FLOW"
    swipe_logical 320 760 320 160 1600
    sleep 1
  done

  # Stay at the same scroll offset while the rendered list settles. Run219's
  # first detector read was transiently empty; the second picker open preserved
  # the offset and seven more drags overshot from Hong Kong to Serbia. Only the
  # screenshot/detector is retried here.
  for detect_attempt in 1 2 3 4; do
    rm -f "$tmp" "$frame"
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if ! python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      echo "short-league Hong Kong frame invalid detect attempt $detect_attempt/4" >> "$FLOW"
      sleep 1
      continue
    fi
    mv -f "$tmp" "$frame"
    cp "$frame" "$OUT/short-league-hong-kong-list.png"
    xy="$(python3 stage4_tools/find_league_picker.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
    if [ "$rc" -eq 0 ]; then
      read -r x y <<<"$xy"
      echo "short-league rendered Hong Kong candidate row ${x},${y}" >> "$FLOW"
      clear_log
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      sleep 2

      rm -f "$tmp" "$post"
      timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
      if python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
        mv -f "$tmp" "$post"
        cp "$post" "$OUT/short-league-hong-kong-selected.png"
        if ! python3 stage4_tools/find_league_picker.py "$post" >/dev/null 2>>"$FLOW"; then
          echo "short-league Hong Kong rendered row accepted" >> "$FLOW"
          return 0
        fi
      fi
      echo "short-league Hong Kong candidate did not close picker" >> "$FLOW"
      return 1
    fi
    echo "short-league Hong Kong first-row detector failed rc=$rc attempt $detect_attempt/4" >> "$FLOW"
    sleep 1
  done

  echo "short-league Hong Kong rendered selection could not be proven" >> "$FLOW"
  return 1
}

continue_after_hong_kong_stock_league(){
  local attempt evidence size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | tail -1)"
  for attempt in 1 2 3; do
    clear_log
    echo "short-league Hong Kong profile Next attempt $attempt/3" >> "$FLOW"
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
       && ! grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*87([^0-9]|$)' "$evidence"; then
      echo "short-league Hong Kong wrong stock nation selected" >> "$FLOW"
      return 1
    fi
    if grep -qE 'List of prospective clubs size:[[:space:]]*0([^0-9]|$)' "$evidence"; then
      echo "short-league Hong Kong produced zero prospective clubs" >> "$FLOW"
      return 1
    fi
    if grep -qE 'GetProspectiveClubs for nation Id:[[:space:]]*87([^0-9]|$)' "$evidence" \
       && grep -qE 'List of prospective clubs size:[[:space:]]*[1-9][0-9]*' "$evidence" \
       && grep -qiE 'LoadDataAndStartTrial|TrialDone|Create Screen:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|SetActive:[[:space:]]*message|CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$evidence"; then
      echo "short-league Hong Kong nation 87 produced viable prospective clubs" >> "$FLOW"
      echo "short-league Hong Kong profile Next stock transition accepted" >> "$FLOW"
      return 0
    fi

    fatal_check || return 1
    echo "short-league Hong Kong profile Next attempt $attempt did not prove bootstrap" >> "$FLOW"
  done
  shot "short-league-next-timeout"
  echo "short-league Hong Kong profile Next timed out" >> "$FLOW"
  return 1
}

select_hong_kong_stock_league || exit 219
continue_after_hong_kong_stock_league || exit 218'''


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
    print(f'Applied stock-UI Hong Kong natural-season selection: {dst}')


if __name__ == '__main__':
    main()
