#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage9-cross-version"
WORK="$RUNNER_TEMP/stage9-fresh-reload-work"
ST7OUT="$RUNNER_TEMP/stage7-persistence"
FLOW="$OUT/STAGE9_FRESH_RELOAD_FLOW.log"
mkdir -p "$OUT" "$WORK"
: > "$FLOW"

ADB_BIN="$(command -v adb)"
adb(){
  { printf '%q ' "$ADB_BIN" "$@"; printf '\n'; } > "$OUT/fresh-reload-last-adb-command.txt"
  command timeout --signal=TERM --kill-after=5s 45s "$ADB_BIN" "$@"
}
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }
fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/fresh-reload-runtime-fatal-logcat.txt" 2>/dev/null || true
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
  return 1
}
logical_xy(){
python3 - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:]); s=subprocess.check_output(['adb','shell','wm','size'],text=True,timeout=15)
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups()); scale=w/640.0; top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_physical(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
press_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); press_physical "$x" "$y" "${3:-2}"; }
press_career(){
  local size; size="$(adb shell wm size 2>/dev/null | tr -d '\r')"
  case "$size" in
    *1080x2280*) press_physical 795 1399 "${1:-2}" ;;
    *) echo "Unsupported Stage9 MainMenu geometry: $size" >&2; return 1 ;;
  esac
}
press_slot0(){ press_logical 332 324 "${1:-3}"; }
dump_save(){
  local tag="$1"
  local remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  local xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || true
  grep -q 'monkeystate' "$xml" || { echo "Could not read durable save for $tag"; return 1; }
  sha256sum "$xml" > "$OUT/${tag}-save.sha256"
}
capture_log(){ local label="$1"; { echo; echo "===== $label ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"; }

# Stage7 setup-only has already created a fresh Career and proved one stock UI
# restart/load. Stage9 performs one more independent process-death reload and
# binds the result to the original fresh save contract.
test -s "$ST7OUT/pre-MonkeyGame.xml"
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null

if wait_log 'LoadCareer saveslot:[[:space:]]*0' 15 stage9-fresh-autoload; then
  wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 30 stage9-fresh-gamemenu
else
  wait_log 'SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu|Create Screen:[[:space:]]*mainmenu' 30 stage9-fresh-mainmenu
  clear_log
  press_career 2
  wait_log 'SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|Create Screen:[[:space:]]*saveslot' 20 stage9-fresh-saveslot
  slot_hit=0
  for slot_attempt in 1 2 3; do
    clear_log
    press_slot0 3
    adb logcat -d -v brief > "$WORK/slot0-attempt-$slot_attempt.txt" 2>/dev/null || true
    if grep -q 'HitGadget: saveslot.btn_Slot0' "$WORK/slot0-attempt-$slot_attempt.txt"; then
      slot_hit=1
      break
    fi
    fatal_check || exit 1
    sleep 1
  done
  [ "$slot_hit" -eq 1 ] || { echo 'Stage9 fresh reload Slot0 did not register'; exit 321; }
  wait_log 'LoadCareer saveslot:[[:space:]]*0' 30 stage9-fresh-loadcareer
  wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 stage9-fresh-gamemenu
fi

fatal_check
capture_log 'fresh save force-stop -> restart -> reload'
dump_save fresh-after-restart
# Literal filename retained for certificate/test binding.
test -s "$OUT/fresh-after-restart-MonkeyGame.xml"
python3 stage8_tools/verify_stage8_lifecycle.py \
  "$ST7OUT/pre-MonkeyGame.xml" \
  "$OUT/fresh-after-restart-MonkeyGame.xml" \
  | tee "$OUT/STAGE9_FRESH_RELOAD_VERIFY.txt"
grep -q 'CAREER_LIFECYCLE_PASS' "$OUT/STAGE9_FRESH_RELOAD_VERIFY.txt"

echo 'VERDICT=STAGE9_FRESH_RELOAD_PASS' | tee "$OUT/STAGE9_FRESH_RELOAD_GATE.txt"
echo 'STAGE9_FRESH_RELOAD_FULL_RUNTIME_PASS'
