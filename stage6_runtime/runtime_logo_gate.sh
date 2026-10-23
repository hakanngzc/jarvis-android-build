#!/usr/bin/env bash
set -euo pipefail

PKG='com.newstargames.newstarsoccer'
ROOT="$PWD"
OUT="$ROOT/stage6_runtime_artifacts/runtime"
SIGNED="$ROOT/stage6_runtime_artifacts/signed"
mkdir -p "$OUT"
SUMMARY="$OUT/stage6-runtime-gates.txt"
LOG="$OUT/runtime-logcat.txt"
: > "$SUMMARY"

record(){ printf '%s=%s\n' "$1" "$2" | tee -a "$SUMMARY"; }
snapshot(){ adb logcat -d -v threadtime > "$LOG" 2>/dev/null || true; }
fatal_check(){
  snapshot
  if grep -qE 'FATAL EXCEPTION|ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer.*has died' "$LOG"; then
    record STAGE6_NO_FATAL FAIL
    return 1
  fi
}
shot(){ adb exec-out screencap -p > "$OUT/$1.png"; }

APKS=("$SIGNED/base.apk")
[ -f "$SIGNED/config.tr.apk" ] && APKS+=("$SIGNED/config.tr.apk")
[ -f "$SIGNED/config.xxhdpi.apk" ] && APKS+=("$SIGNED/config.xxhdpi.apk")
adb install-multiple -r "${APKS[@]}" | tee "$OUT/install.txt"
adb shell pm clear "$PKG" > "$OUT/pm-clear.txt" || true
adb shell wm size > "$OUT/wm-size.txt"
adb logcat -c >/dev/null 2>&1 || true
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb shell am start -n "$PKG/.MonkeyGame" > "$OUT/am-start.txt" 2>&1 || \
  adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 > "$OUT/monkey-start.txt" 2>&1 || true

elapsed=0
all_loaded=0
while [ "$elapsed" -lt 120 ]; do
  fatal_check || { shot stage6-fatal || true; exit 41; }
  if grep -q 'TClub.LoadClub:3141' "$LOG" && \
     grep -q 'TClub.LoadClub:3163' "$LOG" && \
     grep -q 'TClub.LoadClub:3157' "$LOG"; then
    all_loaded=1
    break
  fi
  sleep 2
  elapsed=$((elapsed+2))
done

snapshot
shot stage6-mainmenu-probes
adb shell pidof "$PKG" > "$OUT/pid.txt" 2>/dev/null || true
adb shell dumpsys activity activities > "$OUT/activity.txt" 2>/dev/null || true
grep -E 'TClub\.LoadClub:|Create Screen:|mainmenu|Stage6|FATAL EXCEPTION|ANR in' "$LOG" > "$OUT/runtime-trace.txt" 2>/dev/null || true

if [ "$all_loaded" -ne 1 ]; then
  record STAGE6_REAL_CLUB_LOADS FAIL
  echo 'Did not observe all Stage6 real-club LoadClub probes' >&2
  exit 42
fi
record STAGE6_REAL_CLUB_LOADS PASS
if [ ! -s "$OUT/pid.txt" ]; then
  record STAGE6_PROCESS_ALIVE FAIL
  exit 43
fi
record STAGE6_PROCESS_ALIVE PASS
if [ ! -s "$OUT/stage6-mainmenu-probes.png" ]; then
  record STAGE6_SCREENSHOT_CAPTURE FAIL
  exit 44
fi
record STAGE6_SCREENSHOT_CAPTURE PASS
fatal_check
record STAGE6_NO_FATAL PASS
record STAGE6_RUNTIME_PREFLIGHT PASS
printf 'VERDICT=STAGE6_RUNTIME_PREFLIGHT_PASS\n'
