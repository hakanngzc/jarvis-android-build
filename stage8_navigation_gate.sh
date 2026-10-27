#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage8-navigation"
WORK="$RUNNER_TEMP/stage8-work"
ST7="$RUNNER_TEMP/stage7-work"
FLOW="$OUT/STAGE8_RUNTIME_FLOW.log"
GATE="$OUT/STAGE8_NAVIGATION_GATE.txt"
mkdir -p "$OUT" "$WORK"
: > "$FLOW"; : > "$GATE"

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
  echo "Timed out waiting for $label"; return 1
}
wait_screen(){
  local screen="$1" timeout_s="${2:-30}" pattern="$1"
  case "$screen" in
    shop) pattern='shop|LifestyleShopOverlay' ;;
  esac
  wait_log "SETTING ACTIVE:[[:space:]]*($pattern)([[:space:]]|$)|SetActive:[[:space:]]*($pattern)([[:space:]]|$)" "$timeout_s" "screen-$screen"
}
wait_resumed(){
  local timeout_s="${1:-20}" i
  for i in $(seq 0 "$timeout_s"); do
    adb shell dumpsys activity activities > "$WORK/activity.txt" 2>/dev/null || true
    if grep -qiE 'mResumedActivity.*com\.newstargames\.newstarsoccer/.MonkeyGame|topResumedActivity=.*com\.newstargames\.newstarsoccer/.MonkeyGame' "$WORK/activity.txt"; then return 0; fi
    sleep 1
  done
  cp "$WORK/activity.txt" "$OUT/timeout-resumed-activity.txt" || true
  return 1
}
capture_log(){ local label="$1"; { echo; echo "===== $label ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"; }
logical_xy(){
python3 - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:]);s=subprocess.check_output(['adb','shell','wm','size'],text=True,timeout=15)
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups());scale=w/640.0;top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_logical(){
  local x y; read -r x y < <(logical_xy "$1" "$2")
  adb shell input touchscreen swipe "$x" "$y" "$x" "$y" 220 </dev/null || true
  sleep "${3:-2}"
}
shot(){ adb exec-out screencap -p > "$OUT/$1.png" || true; }
dump_save(){
  local tag="$1"
  local remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  local xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || true
  grep -q 'monkeystate' "$xml" || { echo "Could not read save for $tag"; return 1; }
  sha256sum "$xml" > "$OUT/${tag}-save.sha256"
}
route(){
  local label="$1" lx="$2" ly="$3" target="$4"
  clear_log; press_logical "$lx" "$ly" 2
  wait_screen "$target" 35
  fatal_check; capture_log "$label -> $target"; shot "$label-$target"
  echo "PASS route $label -> $target" | tee -a "$GATE"
}
back_route(){ route "$@"; }

# Stage7 already built a fresh durable Career using the same exact public NSS 4.31 source.
# Remove the Stage7 PlayMatches persistence probe and replace only p_GetAge() with 18 so
# later-career Casino navigation can be exercised without mutating the durable save.
test -f "$ST7/base-career-unsigned.apk"
test -f "$ST7/ci.keystore"
test -f "$ST7/signed/config.tr.apk"
test -f "$ST7/signed/config.xxhdpi.apk"
python3 stage8_tools/patch_stage8_age_unlock.py "$ST7/base-career-unsigned.apk" "$WORK/base-stage8-age-unsigned.apk" | tee "$OUT/stage8-age-unlock.txt"
BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
sign_one(){
  local src="$1" dst="$2" tmp
  tmp="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$tmp"
  "$APKSIGNER" sign --ks "$ST7/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-stage8-age-unsigned.apk" "$WORK/base-stage8-age.apk"
adb install-multiple -r "$WORK/base-stage8-age.apk" "$ST7/signed/config.tr.apk" "$ST7/signed/config.xxhdpi.apk" >/dev/null
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true

# Existing Stage7 slot0 must auto-load back into the Career hub after a process restart.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 stage8-loadcareer
wait_screen gamemenu 60
fatal_check; capture_log 'Stage8 starting GameMenu'; shot stage8-start-gamemenu
dump_save career-lifecycle-pre

# Warm-start must keep the same process and resumed activity.
pid_before="$(adb shell pidof "$PKG" | tr -d '\r')"
test -n "$pid_before"
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
wait_resumed 20
pid_warm="$(adb shell pidof "$PKG" | tr -d '\r')"
[ "$pid_before" = "$pid_warm" ]
echo "PASS warm-start pid=$pid_warm" | tee -a "$GATE"

# Career background/foreground without process death.
adb shell input keyevent 3 >/dev/null
sleep 2
pid_bg="$(adb shell pidof "$PKG" | tr -d '\r')"
[ "$pid_before" = "$pid_bg" ]
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
wait_resumed 20
pid_fg="$(adb shell pidof "$PKG" | tr -d '\r')"
[ "$pid_before" = "$pid_fg" ]
fatal_check; capture_log 'Career lifecycle background -> foreground'; shot stage8-career-foreground
dump_save career-lifecycle-post
python3 stage8_tools/verify_stage8_lifecycle.py "$OUT/career-lifecycle-pre-MonkeyGame.xml" "$OUT/career-lifecycle-post-MonkeyGame.xml" | tee "$OUT/STAGE8_CAREER_LIFECYCLE.txt"
grep -q 'CAREER_LIFECYCLE_PASS' "$OUT/STAGE8_CAREER_LIFECYCLE.txt"
echo 'PASS CAREER_LIFECYCLE_PASS' | tee -a "$GATE"

# Career hub -> Life / Relationships family.
route gamemenu-life 405 837 relationships
route relationships-achievements 561 837 achievements
back_route achievements-back 93 837 relationships
route relationships-lifestyle 249 837 shop
back_route lifestyle-back 93 837 relationships
route relationships-casino 405 837 casino
route casino-blackjack 177 352 blackjack
back_route blackjack-back 93 837 casino
route casino-roulette 469 352 roulette
back_route roulette-back 93 837 casino
route casino-slots 177 586 slots
back_route slots-back 93 837 casino
route casino-racing 469 586 racing
back_route racing-back 93 837 casino
back_route casino-back 93 837 relationships
back_route relationships-home 93 837 gamemenu

# Career hub -> Skills family, including skill-choice and ratings child screens.
route gamemenu-skills 249 837 skills
route skills-skillchoice 580 283 skillchoice
back_route skillchoice-back 93 837 skills
route skills-ratings 405 837 ratings
back_route ratings-back 93 837 skills
back_route skills-home 93 837 gamemenu

# Career hub -> League family and club fixture child.
route gamemenu-league 93 837 league
route league-clubfixtures 249 837 clubfixtures
back_route clubfixtures-league 249 837 league
back_route league-home 93 837 gamemenu

# Normal GameMenu Play route -> LeagueFixtures, then UI Back to the hub.
route gamemenu-leaguefixtures 553 829 leaguefixtures
back_route leaguefixtures-back 93 837 gamemenu

fatal_check
route_passes="$(grep -c '^PASS route ' "$GATE")"
[ "$route_passes" -ge 27 ]
echo "PASS route_count=$route_passes" | tee -a "$GATE"
echo 'VERDICT=STAGE8_CORE_NAVIGATION_RUNTIME_PASS' | tee -a "$GATE"
echo 'STAGE8_NAVIGATION_FULL_RUNTIME_PASS'
