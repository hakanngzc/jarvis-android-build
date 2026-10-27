#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

DRIVER = r'''transport_health_check(){
  local state
  state="$(timeout 8s adb get-state 2>/dev/null || true)"
  [ "$state" = "device" ]
}

capture_valid_live_frame(){
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
  local cycle="$1" elapsed="$2" frame="$WORK/live-chance.png" class rc kind x y frame_w frame_h target_x target_y direction offset min_x max_x min_y max_y event_count now probe_due=0 new_event=0
  : "${LIVE_EVENT_COUNT:=0}"
  : "${LIVE_LAST_PROBE_EPOCH:=0}"

  # Each natural_match_cycle clears logcat immediately before stock Match Play,
  # so elapsed 0/1 is a safe cycle-local reset for the event cursor.
  if [ "$elapsed" -le 1 ]; then
    LIVE_EVENT_COUNT=0
    LIVE_LAST_PROBE_EPOCH=0
  fi

  # Stock runtime publishes player-chance phases through these real screen-state
  # markers. Polling logcat is cheap compared with decoding a 1080x2280 PNG.
  # A new matchminigame/tapball marker triggers an immediate rendered-frame
  # classification; otherwise a bounded periodic probe still catches Half Time,
  # Full Time and visible stock Tutorial callouts that publish no new chance
  # marker.
  timeout 8s adb logcat -d -v brief > "$WORK/live-phase-gate.log" 2>/dev/null || true
  event_count="$(grep -cE 'SETTING ACTIVE:[[:space:]]*(matchminigame|tapball)' "$WORK/live-phase-gate.log" 2>/dev/null || true)"
  [[ "$event_count" =~ ^[0-9]+$ ]] || event_count=0
  [ "$event_count" -le "$LIVE_EVENT_COUNT" ] || new_event=1

  now="$(date +%s)"
  if [ "$LIVE_LAST_PROBE_EPOCH" -eq 0 ] || [ $((now - LIVE_LAST_PROBE_EPOCH)) -ge 8 ]; then
    probe_due=1
  fi
  if [ "$new_event" -eq 0 ] && [ "$probe_due" -eq 0 ]; then
    sleep 0.25
    return 0
  fi
  LIVE_LAST_PROBE_EPOCH="$now"

  if ! capture_valid_live_frame "$frame"; then
    if ! transport_health_check; then
      {
        echo 'STAGE4_EMULATOR_TRANSPORT_DEAD'
        echo "cycle=$cycle elapsed_seconds=$elapsed"
        echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        timeout 8s adb devices -l 2>&1 || true
      } > "$OUT/runtime-transport-dead.txt"
      echo "STAGE4_EMULATOR_TRANSPORT_DEAD cycle=$cycle elapsed=${elapsed}s" >> "$FLOW"
      return 1
    fi
    echo "cycle $cycle valid live frame unavailable @${elapsed}s; transport healthy, retrying on next match loop" >> "$FLOW"
    sleep 1
    return 0
  fi

  # Single-decode classifier preserves the verified detector order. These
  # references are the durable contract used by the regression suite even
  # though classify_live_frame.py now performs the actual single PNG decode:
  # stage4_tools/find_match_resume.py
  # stage4_tools/find_live_ball.py
  # stage4_tools/find_kick_ball.py
  # Visible Tutorial callout is checked before those dimmed match controls.
  class="$(python3 stage4_tools/classify_live_frame.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "cycle $cycle passive live phase @${elapsed}s: no tutorial/resume control/active marker/kick ball" >> "$FLOW"
    # If a fresh stock chance marker arrived before its graphics fully settled,
    # keep the event cursor unconsumed so the next loop retries that same phase.
    if [ "$new_event" -eq 1 ]; then
      sleep 1
    else
      sleep 0.25
    fi
    LIVE_LAST_PROBE_EPOCH="$(date +%s)"
    return 0
  fi
  if [ "$rc" -ne 0 ]; then
    echo "cycle $cycle live-frame classifier failed rc=$rc @${elapsed}s" >> "$FLOW"
    return 1
  fi

  read -r kind x y frame_w frame_h <<<"$class"
  [[ "$frame_w" =~ ^[0-9]+$ && "$frame_h" =~ ^[0-9]+$ ]] || {
    echo "cycle $cycle invalid classifier dimensions '$frame_w'x'$frame_h' @${elapsed}s" >> "$FLOW"
    return 1
  }
  case "$kind" in
    tutorial)
      echo "cycle $cycle stock tutorial overlay ${x},${y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      timeout 8s adb shell input touchscreen tap "$x" "$y" </dev/null || true
      ;;
    resume)
      echo "cycle $cycle match resume Play ${x},${y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      timeout 8s adb shell input touchscreen tap "$x" "$y" </dev/null || true
      ;;
    live)
      : "${LIVE_INPUT_SEQ:=0}"
      LIVE_INPUT_SEQ=$((LIVE_INPUT_SEQ + 1))
      direction=$((LIVE_INPUT_SEQ % 3))
      case "$direction" in
        1) target_x=$((frame_w / 2)) ;;
        2) target_x=$((frame_w / 6)) ;;
        *) target_x=$((frame_w * 5 / 6)) ;;
      esac
      target_y=$((y - frame_h * 22 / 100))
      min_y=$((frame_h * 8 / 100)); max_y=$((frame_h * 77 / 100))
      [ "$target_y" -ge "$min_y" ] || target_y="$min_y"
      [ "$target_y" -le "$max_y" ] || target_y="$max_y"
      echo "cycle $cycle live marker ${x},${y} -> ${target_x},${target_y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      timeout 8s adb shell input touchscreen swipe "$x" "$y" "$target_x" "$target_y" 360 </dev/null || true
      ;;
    kick)
      : "${LIVE_INPUT_SEQ:=0}"
      LIVE_INPUT_SEQ=$((LIVE_INPUT_SEQ + 1))
      direction=$((LIVE_INPUT_SEQ % 3))
      offset=$((frame_w * 7 / 100))
      case "$direction" in
        1) target_x=$((x + offset)) ;;
        2) target_x=$((x - offset)) ;;
        *) target_x="$x" ;;
      esac
      min_x=$((frame_w * 11 / 100)); max_x=$((frame_w * 89 / 100))
      [ "$target_x" -ge "$min_x" ] || target_x="$min_x"
      [ "$target_x" -le "$max_x" ] || target_x="$max_x"
      target_y=$((y - frame_h * 29 / 100))
      min_y=$((frame_h * 10 / 100))
      [ "$target_y" -ge "$min_y" ] || target_y="$min_y"
      echo "cycle $cycle kick ball ${x},${y} -> ${target_x},${target_y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      timeout 8s adb shell input touchscreen swipe "$x" "$y" "$target_x" "$target_y" 360 </dev/null || true
      ;;
    *)
      echo "cycle $cycle unknown live-frame class '$kind' @${elapsed}s" >> "$FLOW"
      return 1
      ;;
  esac

  LIVE_EVENT_COUNT="$event_count"
  LIVE_LAST_PROBE_EPOCH="$(date +%s)"
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

external_browser_active(){
  {
    adb shell dumpsys activity activities 2>/dev/null || true
    adb shell dumpsys window windows 2>/dev/null || true
  } | tr -d '\r' \
    | grep -Ei 'mResumedActivity|topResumedActivity|mCurrentFocus|mFocusedApp' \
    | grep -q 'org.chromium.webview_shell/.WebViewBrowserActivity'
}

dismiss_external_browser_if_present(){
  local step="${1:-?}" attempt
  external_browser_active || return 0
  echo "navigate step $step foreground Facebook WebView detected; Android Back" >> "$FLOW"
  adb shell input keyevent 4 </dev/null || true
  for attempt in 1 2 3; do
    sleep 1
    if ! external_browser_active; then
      echo "navigate step $step Facebook WebView dismissed" >> "$FLOW"
      return 0
    fi
  done
  echo "navigate step $step Facebook WebView remained foreground after bounded dismissal" >> "$FLOW"
  return 1
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

NEW = '''    # Real live-match interaction only. Stock matchminigame/tapball log events
    # gate expensive rendered-frame decoding; an 8-second periodic probe still
    # catches Half Time / Full Time resume controls and visible Tutorial callouts.
    # No match engine, simulate/debug branch or season state is patched.
    drive_live_chance "$cycle" "$elapsed" || return 1'''

NAV_OLD = '''  for step in $(seq 1 50); do
    fatal_check || return 1
    clear_log'''

NAV_NEW = '''  for step in $(seq 1 50); do
    fatal_check || return 1
    dismiss_external_browser_if_present "$step" || return 1
    dismiss_interstitial_if_present "$step" || return 1
    clear_log'''

CYCLE_FAIL_OLD = '''  natural_match_cycle "$cycle" || { echo "natural cycle $cycle failed"; exit 220; }'''
CYCLE_FAIL_NEW = '''  natural_match_cycle "$cycle" || {
    if [ -s "$OUT/runtime-transport-dead.txt" ]; then
      echo 'STAGE4_EMULATOR_TRANSPORT_DEAD'
      exit 222
    fi
    echo "natural cycle $cycle failed"
    exit 220
  }'''

SHOT_OLD = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }\n'
SHOT_NEW = 'shot(){ timeout 8s adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }\n'
FATAL_LOG_OLD = '  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true\n'
FATAL_LOG_NEW = '  timeout 8s adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true\n'
MATCH_LOG_OLD = '    adb logcat -d -v brief > "$WORK/match-live.log" 2>/dev/null || true\n'
MATCH_LOG_NEW = '    timeout 8s adb logcat -d -v brief > "$WORK/match-live.log" 2>/dev/null || true\n'


def harden(text: str) -> str:
    anchor = SHOT_OLD
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

    cycle_fail_count = text.count(CYCLE_FAIL_OLD)
    if cycle_fail_count != 1:
        raise SystemExit(f'expected one natural-cycle failure mapping, found {cycle_fail_count}')
    text = text.replace(CYCLE_FAIL_OLD, CYCLE_FAIL_NEW, 1)

    if 'dismiss_external_browser_if_present "$step"' not in text:
        nav_count = text.count(NAV_OLD)
        if nav_count != 1:
            raise SystemExit(f'expected one navigate-until-match loop, found {nav_count}')
        text = text.replace(NAV_OLD, NAV_NEW, 1)

    if FATAL_LOG_NEW not in text:
        count = text.count(FATAL_LOG_OLD)
        if count != 1:
            raise SystemExit(f'expected one fatal-check adb logcat for watchdog, found {count}')
        text = text.replace(FATAL_LOG_OLD, FATAL_LOG_NEW, 1)
    if MATCH_LOG_NEW not in text:
        count = text.count(MATCH_LOG_OLD)
        if count != 1:
            raise SystemExit(f'expected one live-match adb logcat for watchdog, found {count}')
        text = text.replace(MATCH_LOG_OLD, MATCH_LOG_NEW, 1)
    if SHOT_NEW not in text:
        count = text.count(SHOT_OLD)
        if count != 1:
            raise SystemExit(f'expected one global screenshot helper for watchdog, found {count}')
        text = text.replace(SHOT_OLD, SHOT_NEW, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_live_input.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied log-gated single-decode natural live-match input plus foreground interstitial guard: {dst}')


if __name__ == '__main__':
    main()
