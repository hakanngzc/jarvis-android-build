#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage9-cross-version"
WORK="$RUNNER_TEMP/stage9-cross-version-work"
FLOW="$OUT/STAGE9_POSTMATCH_FLOW.log"
GATE="$OUT/STAGE9_POSTMATCH_GATE.txt"
mkdir -p "$OUT" "$WORK"
: > "$FLOW"
: > "$GATE"

ADB_BIN="$(command -v adb)"
adb(){
  { printf '%q ' "$ADB_BIN" "$@"; printf '\n'; } > "$OUT/last-adb-command.txt"
  command timeout --signal=TERM --kill-after=5s 45s "$ADB_BIN" "$@"
}
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }
fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" 2>/dev/null || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
}
wait_log(){
  local pattern="$1" timeout_s="${2:-30}" label="${3:-$1}" i
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/wait-logcat.txt" 2>/dev/null || true
    if grep -qiE "$pattern" "$WORK/wait-logcat.txt"; then
      echo "Reached $label after ${i}s"
      return 0
    fi
    sleep 1
  done
  cp "$WORK/wait-logcat.txt" "$OUT/timeout-${label//[^A-Za-z0-9_-]/_}.txt" 2>/dev/null || true
  echo "Timed out waiting for $label"
  return 1
}
WM_SIZE="$(adb shell wm size | tr -d '\r')"
logical_xy(){
python3 - "$1" "$2" "$WM_SIZE" <<'PY'
import re,sys
x,y=map(float,sys.argv[1:3]); s=sys.argv[3]
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups())
scale=w/640.0; top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_physical(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
press_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); press_physical "$x" "$y" "${3:-2}"; }
press_play(){ press_logical 553 900 "${1:-2}"; }
press_message_accept(){ press_logical 477 880 "${1:-2}"; }
press_footer_ok(){ press_logical 536 880 "${1:-2}"; }
press_career(){
  local size; size="$(adb shell wm size 2>/dev/null | tr -d '\r')"
  case "$size" in
    *1080x2280*) press_physical 795 1399 "${1:-2}" ;;
    *) press_logical 471 541 "${1:-2}" ;;
  esac
}
press_slot0(){ press_logical 332 324 "${1:-3}"; }
current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line; line="$(grep -Ei 'SETTING ACTIVE:|SetActive:' "$WORK/state.log" | tail -1 || true)"
  case "${line,,}" in
    *matchstats*) echo matchstats;;
    *matchreview*) echo matchreview;;
    *gamemenu*) echo gamemenu;;
    *leaguefixtures*) echo leaguefixtures;;
    *message*) echo message;;
    *contract*) echo contract;;
    *webpage*) echo webpage;;
    *startransition*) echo startransition;;
    *" active: league"*|*"setactive: league"*) echo league;;
    *) echo unknown;;
  esac
}
wait_state(){
  local wanted="$1" timeout_s="${2:-30}" i state
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    state="$(current_state)"
    if [[ " $wanted " == *" $state "* ]]; then
      echo "$state"
      return 0
    fi
    sleep 1
  done
  echo unknown
  return 1
}
capture_log(){ local label="$1"; { echo; echo "===== $label ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"; }
shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }
dump_save(){
  local tag="$1"
  local remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  local xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || true
  grep -q 'monkeystate' "$xml" || { echo "Could not read durable save for $tag"; return 1; }
  sha256sum "$xml" > "$OUT/${tag}-save.sha256"
}
open_slot0_if_needed(){
  local slot_attempt slot_hit=0
  if wait_log 'LoadCareer saveslot:[[:space:]]*0' 12 stage9-auto-loadcareer; then
    return 0
  fi
  wait_log 'SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 30 stage9-restart-mainmenu
  clear_log
  press_career 2
  wait_log 'SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 20 stage9-restart-saveslot
  for slot_attempt in 1 2 3; do
    clear_log
    press_slot0 3
    adb logcat -d -v brief > "$WORK/restart-slot0-attempt-$slot_attempt.txt" 2>/dev/null || true
    if grep -q 'HitGadget: saveslot.btn_Slot0' "$WORK/restart-slot0-attempt-$slot_attempt.txt"; then
      slot_hit=1
      break
    fi
    fatal_check || return 1
    sleep 1
  done
  [ "$slot_hit" -eq 1 ] || { echo 'Restart Slot0 gadget did not register'; return 1; }
  wait_log 'LoadCareer saveslot:[[:space:]]*0' 30 stage9-restart-loadcareer
}

# Stage8 match lifecycle finishes on the real stock MatchStats screen.
fatal_check
wait_state 'matchstats' 15 >/dev/null
shot stage9-matchstats-entry

# MatchStats -> MatchReview must be a real active transition, not preallocation.
clear_log
press_play 2
wait_state 'matchreview' 30 >/dev/null
fatal_check
capture_log 'MatchStats -> MatchReview'
shot stage9-matchreview

echo 'STAGE9_MATCHREVIEW_REACHED' | tee -a "$GATE"

# Continue stock post-match flow until the Career hub returns. Keep logcat intact
# after leaving MatchReview so any stock SaveCareer marker remains observable.
clear_log
press_play 2
state="$(current_state)"
for step in $(seq 1 40); do
  fatal_check || exit 401
  state="$(current_state)"
  [ "$state" = gamemenu ] && break
  case "$state" in
    matchreview|leaguefixtures|league) press_play 2;;
    message|startransition) press_message_accept 2;;
    contract|webpage) press_footer_ok 2;;
    unknown) sleep 1; press_play 1;;
    *) press_play 2;;
  esac
  sleep 1
done
[ "$(current_state)" = gamemenu ] || { capture_log 'postmatch did not return to GameMenu'; shot stage9-postmatch-gamemenu-failure; exit 402; }
wait_log 'SAVE CAREER|SaveCareer|SaveState' 30 stage9-postmatch-save
fatal_check
capture_log 'postmatch returned to GameMenu with stock save'
shot stage9-postmatch-gamemenu

dump_save postmatch-before-restart
# Literal evidence paths are intentionally explicit for the Stage9 certificate.
test -s "$OUT/postmatch-before-restart-MonkeyGame.xml"

# Force process death and reload exactly the durable post-match Career.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
open_slot0_if_needed
wait_log 'LoadCareer saveslot:[[:space:]]*0' 30 stage9-loadcareer-after-restart
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 45 stage9-gamemenu-after-restart
fatal_check
capture_log 'postmatch force-stop -> restart -> reload'
shot stage9-postmatch-after-restart

dump_save postmatch-after-restart
test -s "$OUT/postmatch-after-restart-MonkeyGame.xml"
python3 stage8_tools/verify_stage8_lifecycle.py \
  "$OUT/postmatch-before-restart-MonkeyGame.xml" \
  "$OUT/postmatch-after-restart-MonkeyGame.xml" \
  | tee "$OUT/STAGE9_POSTMATCH_RELOAD_VERIFY.txt"
grep -q 'CAREER_LIFECYCLE_PASS' "$OUT/STAGE9_POSTMATCH_RELOAD_VERIFY.txt"

{
  echo 'STAGE9_POSTMATCH_RELOAD_PASS'
  echo 'VERDICT=STAGE9_POSTMATCH_GATE_PASS'
} | tee -a "$GATE"
echo 'STAGE9_POSTMATCH_FULL_RUNTIME_PASS'
