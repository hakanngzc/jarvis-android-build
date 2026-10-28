#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage8-match-lifecycle"
WORK="$RUNNER_TEMP/stage8-match-work"
ST7="$RUNNER_TEMP/stage7-work"
FLOW="$OUT/STAGE8_MATCH_LIFECYCLE_FLOW.log"
ENTRY_TRACE="$OUT/STAGE8_MATCH_ENTRY_TRACE.txt"
mkdir -p "$OUT" "$WORK"
: > "$FLOW"
: > "$ENTRY_TRACE"

ADB_BIN="$(command -v adb)"
adb(){
  { printf '%q ' "$ADB_BIN" "$@"; printf '\n'; } > "$OUT/last-adb-command.txt"
  command timeout --signal=TERM --kill-after=5s 45s "$ADB_BIN" "$@"
}
WM_SIZE="$(adb shell wm size | tr -d '\r')"
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }
fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'; return 1
  fi
}
wait_log(){
  local pattern="$1" timeout_s="${2:-30}" label="${3:-$1}" i
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/wait-logcat.txt" 2>/dev/null || true
    if grep -qiE "$pattern" "$WORK/wait-logcat.txt"; then echo "Reached $label after ${i}s"; return 0; fi
    sleep 1
  done
  cp "$WORK/wait-logcat.txt" "$OUT/timeout-${label//[^A-Za-z0-9_-]/_}.txt" 2>/dev/null || true
  return 1
}
wait_rendered_frame(){
  local timeout_s="${1:-30}" i bytes stable=0
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    adb exec-out screencap -p > "$WORK/render-ready.png" 2>/dev/null || true
    bytes="$(wc -c < "$WORK/render-ready.png")"
    if [ "$bytes" -ge 50000 ]; then
      stable=$((stable+1))
      if [ "$stable" -ge 3 ]; then
        echo "Stable rendered match frame ready after ${i}s (${bytes} bytes)"
        return 0
      fi
    else
      stable=0
    fi
    sleep 1
  done
  cp "$WORK/render-ready.png" "$OUT/timeout-match-render-ready.png" 2>/dev/null || true
  echo 'Timed out waiting for stable rendered match frame'
  return 1
}
transport_health_check(){
  local state
  state="$(adb get-state 2>/dev/null || true)"
  [ "$state" = device ]
}
capture_valid_live_frame(){
  local final="$1" tmp attempt
  tmp="${final}.tmp"
  rm -f "$tmp" "$final"
  for attempt in 1 2 3; do
    rm -f "$tmp"
    adb exec-out screencap -p > "$tmp" 2>/dev/null || true
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
  local cycle="$1" elapsed="${2:-0}" frame="$WORK/live-chance.png" class rc kind x y frame_w frame_h target_x target_y direction offset min_x max_x min_y max_y event_count now probe_due=0 new_event=0
  : "${LIVE_EVENT_COUNT:=0}"
  : "${LIVE_LAST_PROBE_EPOCH:=0}"

  adb logcat -d -v brief > "$WORK/live-phase-gate.log" 2>/dev/null || true
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
        echo 'STAGE8_EMULATOR_TRANSPORT_DEAD'
        echo "cycle=$cycle elapsed_seconds=$elapsed"
        echo "utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
        adb devices -l 2>&1 || true
      } > "$OUT/runtime-transport-dead.txt"
      echo "STAGE8_EMULATOR_TRANSPORT_DEAD cycle=$cycle elapsed=${elapsed}s" >> "$FLOW"
      return 1
    fi
    echo "cycle $cycle valid live frame unavailable @${elapsed}s; transport healthy" >> "$FLOW"
    sleep 1
    return 0
  fi

  class="$(python3 stage4_tools/classify_live_frame.py "$frame" 2>>"$FLOW")" && rc=0 || rc=$?
  if [ "$rc" -eq 1 ]; then
    echo "cycle $cycle passive live phase @${elapsed}s" >> "$FLOW"
    if [ "$new_event" -eq 1 ]; then sleep 1; else sleep 0.25; fi
    LIVE_LAST_PROBE_EPOCH="$(date +%s)"
    return 0
  fi
  if [ "$rc" -ne 0 ]; then
    echo "cycle $cycle live-frame classifier failed rc=$rc @${elapsed}s" >> "$FLOW"
    return 1
  fi

  read -r kind x y frame_w frame_h <<<"$class"
  [[ "$frame_w" =~ ^[0-9]+$ && "$frame_h" =~ ^[0-9]+$ ]] || return 1
  case "$kind" in
    tutorial)
      echo "cycle $cycle stock tutorial overlay ${x},${y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      ;;
    resume)
      echo "cycle $cycle match resume Play ${x},${y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      adb shell input touchscreen tap "$x" "$y" </dev/null || true
      ;;
    live)
      : "${LIVE_INPUT_SEQ:=0}"
      LIVE_INPUT_SEQ=$((LIVE_INPUT_SEQ + 1))
      direction=$((LIVE_INPUT_SEQ % 3))
      case "$direction" in
        1) target_x=$((frame_w / 2));;
        2) target_x=$((frame_w / 6));;
        *) target_x=$((frame_w * 5 / 6));;
      esac
      target_y=$((y - frame_h * 22 / 100))
      min_y=$((frame_h * 8 / 100)); max_y=$((frame_h * 77 / 100))
      [ "$target_y" -ge "$min_y" ] || target_y="$min_y"
      [ "$target_y" -le "$max_y" ] || target_y="$max_y"
      echo "cycle $cycle live marker ${x},${y} -> ${target_x},${target_y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      adb shell input touchscreen swipe "$x" "$y" "$target_x" "$target_y" 360 </dev/null || true
      ;;
    kick)
      : "${LIVE_INPUT_SEQ:=0}"
      LIVE_INPUT_SEQ=$((LIVE_INPUT_SEQ + 1))
      direction=$((LIVE_INPUT_SEQ % 3)); offset=$((frame_w * 7 / 100))
      case "$direction" in
        1) target_x=$((x + offset));;
        2) target_x=$((x - offset));;
        *) target_x="$x";;
      esac
      min_x=$((frame_w * 11 / 100)); max_x=$((frame_w * 89 / 100))
      [ "$target_x" -ge "$min_x" ] || target_x="$min_x"
      [ "$target_x" -le "$max_x" ] || target_x="$max_x"
      target_y=$((y - frame_h * 29 / 100)); min_y=$((frame_h * 10 / 100))
      [ "$target_y" -ge "$min_y" ] || target_y="$min_y"
      echo "cycle $cycle kick ball ${x},${y} -> ${target_x},${target_y} frame=${frame_w}x${frame_h} @${elapsed}s" >> "$FLOW"
      adb shell input touchscreen swipe "$x" "$y" "$target_x" "$target_y" 360 </dev/null || true
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
logical_xy(){
python3 - "$1" "$2" "$WM_SIZE" <<'PY'
import re,sys
x,y=map(float,sys.argv[1:3])
s=sys.argv[3]
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups())
scale=w/640.0; top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_physical(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
press_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); press_physical "$x" "$y" "${3:-2}"; }
press_play(){ press_logical 553 900 "${1:-2}"; }
press_fixture_play(){ press_logical 553 900 "${1:-2}"; }
press_message_accept(){ press_logical 477 880 "${1:-2}"; }
start_live_match(){
  local attempt
  for attempt in 1 2 3; do
    clear_log
    press_play 1
    if wait_log 'HitGadget:[[:space:]]*match\.btn_Play' 5 "match-play-$attempt"; then
      return 0
    fi
  done
  capture_log 'failed to hit stock match Play gadget'
  shot stage8-match-play-failure
  return 1
}
current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line; line="$(grep -Ei 'SETTING ACTIVE:|SetActive:' "$WORK/state.log" | tail -1 || true)"
  case "${line,,}" in
    *matchstats*) echo matchstats;;
    *matchreview*) echo matchreview;;
    *leaguefixtures*) echo leaguefixtures;;
    *gamemenu*) echo gamemenu;;
    *message*) echo message;;
    *" active: match"*|*"setactive: match"*) echo match;;
    *" active: league"*|*"setactive: league"*) echo league;;
    *) echo unknown;;
  esac
}
wait_state(){
  local wanted="$1" timeout_s="${2:-30}" i state
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    state="$(current_state)"
    if [[ " $wanted " == *" $state "* ]]; then echo "$state"; return 0; fi
    sleep 1
  done
  echo unknown; return 1
}
wait_resumed(){
  local timeout_s="${1:-20}" i
  for i in $(seq 0 "$timeout_s"); do
    adb shell dumpsys activity activities > "$WORK/activity.txt" 2>/dev/null || true
    if grep -qiE 'mResumedActivity.*com\.newstargames\.newstarsoccer/.MonkeyGame|topResumedActivity=.*com\.newstargames\.newstarsoccer/.MonkeyGame' "$WORK/activity.txt"; then return 0; fi
    sleep 1
  done
  cp "$WORK/activity.txt" "$OUT/timeout-resumed-activity.txt" 2>/dev/null || true
  return 1
}
shot(){ adb exec-out screencap -p > "$OUT/$1.png" || true; }
capture_log(){ local label="$1"; { echo; echo "===== $label ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"; }

# Reinstall the Stage7 same-signature base that has FTUE/trial harnessing only.
# It does NOT patch c_TMatch.m_StartMatch or the live match engine.
test -f "$ST7/signed/base-career.apk"
test -f "$ST7/signed/config.tr.apk"
test -f "$ST7/signed/config.xxhdpi.apk"
adb install-multiple -r "$ST7/signed/base-career.apk" "$ST7/signed/config.tr.apk" "$ST7/signed/config.xxhdpi.apk" >/dev/null
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 lifecycle-loadcareer
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 lifecycle-gamemenu

# Reach a real Career fixture using the stock route.
LEAGUEFIXTURES_REACHED=0
for attempt in 1 2; do
  clear_log
  press_play 4
  if wait_log 'SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 12 "leaguefixtures-attempt-$attempt"; then
    LEAGUEFIXTURES_REACHED=1
    break
  fi
  adb logcat -d -v brief > "$WORK/leaguefixtures-attempt-$attempt.log" 2>/dev/null || true
  if grep -qiE 'SETTING ACTIVE:[[:space:]]*message|SetActive:[[:space:]]*message' "$WORK/leaguefixtures-attempt-$attempt.log"; then
    press_message_accept 3
  fi
done
if [ "$LEAGUEFIXTURES_REACHED" -ne 1 ]; then
  capture_log 'failed GameMenu -> LeagueFixtures'
  shot stage8-match-leaguefixtures-failure
  echo 'Did not reach LeagueFixtures through proven GameMenu Play route'
  exit 302
fi
capture_log 'GameMenu -> LeagueFixtures direct activation proof'
state=leaguefixtures

MATCH_REACHED=0
for step in $(seq 1 24); do
  echo "step=$step before=$state" >> "$ENTRY_TRACE"
  clear_log
  case "$state" in
    leaguefixtures) press_fixture_play 3;;
    gamemenu|league) press_play 3;;
    message) press_message_accept 3;;
    *) sleep 2;;
  esac
  state="$(wait_state 'match message leaguefixtures league gamemenu' 20 || true)"
  adb logcat -d -v brief > "$WORK/entry-step-$step.log" 2>/dev/null || true
  last_event="$(grep -Ei 'HitGadget:|SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/entry-step-$step.log" | tail -1 || true)"
  echo "step=$step after=$state last=${last_event:-NONE}" >> "$ENTRY_TRACE"
  if [ "$state" = match ]; then MATCH_REACHED=1; break; fi
done
[ "$MATCH_REACHED" -eq 1 ] || { capture_log 'failed to reach playable Career match'; shot stage8-match-entry-failure; echo 'No playable Career match reached'; exit 303; }
shot stage8-match-prematch

# Start the untouched live match, then exercise Android background/foreground.
start_live_match || { echo 'Stock match Play gadget was not reached'; exit 304; }
sleep 2
fatal_check; capture_log 'stock live match started'; shot stage8-match-before-background

pid_before="$(adb shell pidof "$PKG" | tr -d '\r')"
test -n "$pid_before"
adb shell input keyevent 3 >/dev/null
sleep 2
pid_bg="$(adb shell pidof "$PKG" | tr -d '\r')"
[ "$pid_before" = "$pid_bg" ]
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
wait_resumed 20
wait_rendered_frame 30
pid_fg="$(adb shell pidof "$PKG" | tr -d '\r')"
[ "$pid_before" = "$pid_fg" ]
fatal_check; capture_log 'live match background -> foreground'; shot stage8-match-after-background

# Prove the resumed live match remains functional by naturally continuing it to
# the stock MatchStats screen. No score/time/match-state field is patched.
MATCHSTATS_REACHED=0
NATURAL_CYCLES=0
LIVE_START_EPOCH="$(date +%s)"
LIVE_EVENT_COUNT=0
LIVE_LAST_PROBE_EPOCH=0
LIVE_INPUT_SEQ=0
for cycle in $(seq 1 900); do
  NATURAL_CYCLES="$cycle"
  fatal_check || exit 305
  state="$(current_state)"
  if [ "$state" = matchstats ]; then MATCHSTATS_REACHED=1; break; fi
  case "$state" in
    message) press_message_accept 0.2;;
    leaguefixtures|league|gamemenu|matchreview) echo "Match left before MatchStats: $state"; exit 306;;
  esac
  elapsed=$(( $(date +%s) - LIVE_START_EPOCH ))
  if [ "$elapsed" -ge 720 ]; then
    echo "Natural match wall-clock limit reached after ${elapsed}s" >> "$FLOW"
    break
  fi
  drive_live_chance "$cycle" "$elapsed" || exit 305
  if [ $((cycle % 30)) -eq 0 ]; then capture_log "post-lifecycle natural cycle $cycle state=$state elapsed=${elapsed}s"; fi
  sleep 0.25
done
[ "$MATCHSTATS_REACHED" -eq 1 ] || { echo "No MatchStats after $NATURAL_CYCLES cycles"; capture_log 'match lifecycle ended without MatchStats'; shot stage8-matchstats-timeout; exit 307; }
[ "$NATURAL_CYCLES" -ge 3 ]
fatal_check; capture_log "post-lifecycle match reached MatchStats after $NATURAL_CYCLES cycles"; shot stage8-matchstats-after-lifecycle

{
  echo "PASS MATCH_BACKGROUND_FOREGROUND_SAME_PROCESS pid=$pid_fg"
  echo "PASS MATCH_CONTINUED_TO_MATCHSTATS cycles=$NATURAL_CYCLES"
  echo 'VERDICT=STAGE8_MATCH_LIFECYCLE_PASS'
} | tee "$OUT/STAGE8_MATCH_LIFECYCLE_GATE.txt"
echo 'STAGE8_MATCH_LIFECYCLE_FULL_RUNTIME_PASS'
