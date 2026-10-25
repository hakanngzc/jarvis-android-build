#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

DRIVER = r'''capture_valid_live_frame(){
  local final="$1" tmp attempt
  tmp="${final}.tmp"
  rm -f "$tmp" "$final"
  for attempt in 1 2 3; do
    rm -f "$tmp"
    timeout 8s adb exec-out screencap -p > "$tmp" 2>/dev/null || true
    if python3 stage4_tools/validate_frame_png.py "$tmp" 2>>"$FLOW"; then
      mv -f "$tmp" "$final"
      return 0
    fi
    echo "live frame capture retry $attempt/3" >> "$FLOW"
    sleep 1
  done
  rm -f "$tmp"
  return 1
}

drive_live_chance(){
  local cycle="$1" elapsed="$2" frame="$WORK/live-chance.png" class rc kind x y target_x target_y direction
  if ! capture_valid_live_frame "$frame"; then
    echo "cycle $cycle valid live frame unavailable @${elapsed}s; retrying on next match loop" >> "$FLOW"
    sleep 1
    return 0
  fi

  # Single-decode classifier preserves the previously verified priority:
  # stage4_tools/find_match_resume.py
  # stage4_tools/find_live_ball.py
  # stage4_tools/find_kick_ball.py
  class="$(python3 stage4_tools/classify_live_frame.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "cycle $cycle passive live phase @${elapsed}s: no resume control/active marker/kick ball" >> "$FLOW"
    sleep 1
    return 0
  fi
  if [ "$rc" -ne 0 ]; then
    echo "cycle $cycle live-frame classifier failed rc=$rc @${elapsed}s" >> "$FLOW"
    return 1
  fi

  read -r kind x y <<<"$class"
  case "$kind" in
    resume)
      echo "cycle $cycle match resume Play ${x},${y} @${elapsed}s" >> "$FLOW"
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      ;;
    live)
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
      ;;
    kick)
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
      ;;
    *)
      echo "cycle $cycle unknown live-frame class '$kind' @${elapsed}s" >> "$FLOW"
      return 1
      ;;
  esac
  sleep 1
  return 0
}
'''

AD_GUARD = r'''ad_activity_active(){
  {
    adb shell dumpsys activity activities 2>/dev/null || true
    adb shell dumpsys window windows 2>/dev/null || true
  } | tr -d '\r' \
    | grep -Ei 'mResumedActivity|topResumedActivity|mCurrentFocus|mFocusedApp' \
    | grep -q 'com.newstargames.newstarsoccer/com.google.android.gms.ads.AdActivity'
}

dismiss_interstitial_if_present(){
  local step="${1:-?}" attempt size w h x y
  ad_activity_active || return 0
  echo "navigate step $step foreground AdActivity detected; dismissing stock interstitial" >> "$FLOW"

  adb shell input keyevent 4 </dev/null || true
  for attempt in 1 2 3; do
    sleep 1
    if ! ad_activity_active; then
      echo "navigate step $step interstitial dismissed with Android Back" >> "$FLOW"
      return 0
    fi
  done

  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | sed -n 's/.*: \([0-9][0-9]*\)x\([0-9][0-9]*\).*/\1 \2/p' | tail -1 || true)"
  read -r w h <<<"$size"
  if [[ "${w:-}" =~ ^[0-9]+$ && "${h:-}" =~ ^[0-9]+$ ]]; then
    x=$((w * 958 / 1000))
    y=$((h * 35 / 1000))
  else
    x=1035; y=80
  fi
  echo "navigate step $step interstitial close fallback tap ${x},${y}" >> "$FLOW"
  adb shell input touchscreen tap "$x" "$y" </dev/null || true
  for attempt in 1 2 3 4 5; do
    sleep 1
    if ! ad_activity_active; then
      echo "navigate step $step interstitial dismissed with close control" >> "$FLOW"
      return 0
    fi
  done

  echo "navigate step $step interstitial remained foreground after bounded dismissal" >> "$FLOW"
  return 1
}
'''

OLD = '''    # Real live-match interaction only: ordinary touchscreen swipes/taps. No
    # match engine method is patched and no hidden simulate/debug branch is used.
    swipe_logical 320 700 320 250 420; sleep 1
    swipe_logical 260 690 460 280 380; sleep 1
    swipe_logical 380 690 180 280 380; sleep 1
    press_logical 320 600 1'''

NEW = '''    # Real live-match interaction only. One validated rendered frame is
    # classified once into resume/active-marker/kick-ball input. No match
    # engine, simulate/debug branch or season state is patched.
    drive_live_chance "$cycle" "$elapsed"'''

NAV_OLD = '''  for step in $(seq 1 50); do
    fatal_check || return 1
    clear_log'''

NAV_NEW = '''  for step in $(seq 1 50); do
    fatal_check || return 1
    dismiss_interstitial_if_present "$step" || return 1
    clear_log'''


def harden(text: str) -> str:
    anchor = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }\n'
    if 'drive_live_chance(){' not in text:
        if text.count(anchor) != 1:
            raise SystemExit(f'expected one shot helper anchor for live driver, found {text.count(anchor)}')
        text = text.replace(anchor, anchor + DRIVER + '\n', 1)
    if 'dismiss_interstitial_if_present(){' not in text:
        if text.count(anchor) != 1:
            raise SystemExit(f'expected one shot helper anchor for ad guard, found {text.count(anchor)}')
        text = text.replace(anchor, anchor + AD_GUARD + '\n', 1)

    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f'expected one fixed live-input block, found {count}')
    text = text.replace(OLD, NEW, 1)

    if 'dismiss_interstitial_if_present "$step"' not in text:
        nav_count = text.count(NAV_OLD)
        if nav_count != 1:
            raise SystemExit(f'expected one navigate-until-match loop, found {nav_count}')
        text = text.replace(NAV_OLD, NAV_NEW, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_live_input.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied single-decode validated-frame natural live-match input plus foreground interstitial guard: {dst}')


if __name__ == '__main__':
    main()
