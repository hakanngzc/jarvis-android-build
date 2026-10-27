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
logical_xy(){
python3 - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:])
s=subprocess.check_output(['adb','shell','wm','size'],text=True,timeout=15)
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
quick_tap_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); adb shell input tap "$x" "$y" </dev/null >/dev/null 2>&1 || true; }
quick_swipe_logical(){
  local x1 y1 x2 y2
  read -r x1 y1 < <(logical_xy "$1" "$2")
  read -r x2 y2 < <(logical_xy "$3" "$4")
  adb shell input touchscreen swipe "$x1" "$y1" "$x2" "$y2" "${5:-240}" </dev/null >/dev/null 2>&1 || true
}
natural_input_burst(){
  quick_swipe_logical 320 620 320 300 260
  sleep 0.18
  for p in '180 430' '260 430' '340 430' '420 430' '180 520' '260 520' '340 520' '420 520' '220 610' '320 610' '420 610'; do
    # shellcheck disable=SC2086
    quick_tap_logical $p
    sleep 0.05
  done
  quick_swipe_logical 230 610 450 330 220
  quick_swipe_logical 410 610 190 330 220
  quick_tap_logical 160 790
  quick_tap_logical 320 790
  quick_tap_logical 480 790
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
pid_fg="$(adb shell pidof "$PKG" | tr -d '\r')"
[ "$pid_before" = "$pid_fg" ]
fatal_check; capture_log 'live match background -> foreground'; shot stage8-match-after-background

# Prove the resumed live match remains functional by naturally continuing it to
# the stock MatchStats screen. No score/time/match-state field is patched.
MATCHSTATS_REACHED=0
NATURAL_CYCLES=0
for cycle in $(seq 1 360); do
  NATURAL_CYCLES="$cycle"
  fatal_check || exit 305
  state="$(current_state)"
  if [ "$state" = matchstats ]; then MATCHSTATS_REACHED=1; break; fi
  case "$state" in
    message) press_message_accept 0.2;;
    match|unknown) press_play 0.15; natural_input_burst;;
    leaguefixtures|league|gamemenu|matchreview) echo "Match left before MatchStats: $state"; exit 306;;
    *) natural_input_burst;;
  esac
  if [ $((cycle % 30)) -eq 0 ]; then capture_log "post-lifecycle natural cycle $cycle state=$state"; fi
  sleep 0.65
done
[ "$MATCHSTATS_REACHED" -eq 1 ] || { echo "No MatchStats after $NATURAL_CYCLES cycles"; exit 307; }
[ "$NATURAL_CYCLES" -ge 3 ]
fatal_check; capture_log "post-lifecycle match reached MatchStats after $NATURAL_CYCLES cycles"; shot stage8-matchstats-after-lifecycle

{
  echo "PASS MATCH_BACKGROUND_FOREGROUND_SAME_PROCESS pid=$pid_fg"
  echo "PASS MATCH_CONTINUED_TO_MATCHSTATS cycles=$NATURAL_CYCLES"
  echo 'VERDICT=STAGE8_MATCH_LIFECYCLE_PASS'
} | tee "$OUT/STAGE8_MATCH_LIFECYCLE_GATE.txt"
echo 'STAGE8_MATCH_LIFECYCLE_FULL_RUNTIME_PASS'
