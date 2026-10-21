#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage3-minimal"
WORK="$RUNNER_TEMP/stage3-work"
FLOW="$OUT/STAGE3_RUNTIME_FLOW.log"
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
: > "$FLOW"

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

capture_log(){
  local label="$1"
  { echo; echo "===== $label ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"
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
logical_xy(){
python3 - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:]); s=subprocess.check_output(['adb','shell','wm','size'],text=True)
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups()); scale=w/640.0; top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_physical(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
press_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); press_physical "$x" "$y" "${3:-2}"; }
press_career(){ press_logical 471 541 "${1:-3}"; }
press_slot0(){ press_logical 332 324 "${1:-3}"; }
press_footer_ok(){ press_logical 536 880 "${1:-2}"; }
press_message_accept(){ press_logical 477 880 "${1:-2}"; }
press_play(){ press_logical 553 829 "${1:-3}"; }
shot(){ adb exec-out screencap -p > "$OUT/$1.png" || true; }

start_game(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"
  sleep 3
  test -n "$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  capture_log "$tag mainmenu"
  shot "$tag-mainmenu"
}
open_slot0(){
  local tag="$1"
  clear_log; press_career 3
  wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 30 "$tag-saveslot"
  capture_log "$tag saveslot"; shot "$tag-saveslot"
  clear_log; press_slot0 3
}
load_existing(){
  local tag="$1"
  sleep 2; adb logcat -d -v brief > "$WORK/$tag-load.txt" 2>/dev/null || true
  if ! grep -q 'LoadCareer saveslot: 0' "$WORK/$tag-load.txt"; then press_message_accept 3; fi
  wait_log 'LoadCareer saveslot: 0' 30 "$tag-loadcareer"
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 "$tag-gamemenu"
  capture_log "$tag load existing"; shot "$tag-loaded"
}
current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line; line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  case "${line,,}" in
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;;
    *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;; *) echo unknown;;
  esac
}
wait_state(){
  local wanted="$1" timeout_s="${2:-30}" i state
  for i in $(seq 0 "$timeout_s"); do fatal_check || return 1; state="$(current_state)"; if [[ " $wanted " == *" $state "* ]]; then echo "$state"; return 0; fi; sleep 1; done
  capture_log "timeout state $wanted"; echo unknown; return 1
}
dump_save(){
  local tag="$1" remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml" xml="$OUT/${tag}-MonkeyGame.xml"
  if adb shell cat "$remote" > "$xml" 2>/dev/null && grep -q 'monkeystate' "$xml"; then :; else echo "Could not read $remote"; return 1; fi
  echo "Captured $tag save"
}

# Exact public 4.31 source.
curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$WORK/nss431.xapk"
echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c -
unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$BASE_SHA  $BASE" | sha256sum -c -

# Test-only deterministic Career/Trial shortcuts. Save/load and match writeback remain stock.
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/career-trial-patch.txt"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci -dname 'CN=NSS Stage3 CI' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")"; "$ZIPALIGN" -f 4 "$src" "$tmp"; "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"; "$APKSIGNER" verify --verbose "$dst" >/dev/null; }
sign_one "$WORK/base-career-unsigned.apk" "$WORK/signed/base-career.apk"
sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"
sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"
install_base(){ adb install-multiple -r "$1" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" >/dev/null; }
install_base "$WORK/signed/base-career.apk"
adb shell pm clear "$PKG" >/dev/null || true
adb root >/dev/null 2>&1 || true; adb wait-for-device; sleep 2

# Fresh stock Career creation.
start_game fresh
open_slot0 fresh
wait_log 'Create Screen:[[:space:]]*chooseclub|SETTING ACTIVE:[[:space:]]*chooseclub|SetActive:[[:space:]]*chooseclub' 30 chooseclub
for _ in 1 2 3 4; do
  adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true
  grep -qiE 'choosenation' "$WORK/setup.txt" && break
  press_footer_ok 2; fatal_check
done
wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
clear_log; press_footer_ok 2
wait_log 'LoadDataAndStartTrial|TrialDone|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|Create Screen:[[:space:]]*message' 30 'career message'
for _ in 1 2 3 4; do
  press_message_accept 2; fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/save-progress.txt"; then break; fi
done
sleep 3; capture_log 'fresh Career saved'
if ! grep -qEi 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$FLOW"; then echo 'Fresh Career save evidence missing'; exit 108; fi
wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 fresh-gamemenu || true
shot fresh-after-save

# Same-signature Stage3 fast-match update.
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_stage3_fast_match_probe.py "$WORK/base-career-unsigned.apk" "$WORK/base-stage3-unsigned.apk" | tee "$OUT/stage3-fast-match-patch.txt"
sign_one "$WORK/base-stage3-unsigned.apk" "$WORK/signed/base-stage3.apk"
install_base "$WORK/signed/base-stage3.apk"
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true

start_game stage3
open_slot0 stage3
load_existing stage3
dump_save pre-match

# GameMenu -> LeagueFixtures.
clear_log; press_play 3
state="$(wait_state 'leaguefixtures message gamemenu' 30 || true)"; capture_log "GameMenu Play -> $state"
if [ "$state" = message ]; then clear_log; press_message_accept 3; state="$(wait_state 'leaguefixtures gamemenu' 30 || true)"; capture_log "message -> $state"; fi
if [ "$state" = gamemenu ]; then clear_log; press_play 3; state="$(wait_state 'leaguefixtures message' 30 || true)"; capture_log "second Play -> $state"; fi
[ "$state" = leaguefixtures ] || { echo "Did not reach LeagueFixtures: $state"; exit 202; }
shot stage3-leaguefixtures

MATCH_REACHED=0
for step in $(seq 1 24); do
  clear_log
  case "$state" in leaguefixtures|gamemenu|league) press_play 3;; message) press_message_accept 3;; *) sleep 2;; esac
  state="$(wait_state 'match message leaguefixtures league gamemenu' 20 || true)"; capture_log "pre-match step $step -> $state"
  if [ "$state" = match ]; then MATCH_REACHED=1; break; fi
done
[ "$MATCH_REACHED" -eq 1 ] || { echo 'No playable Career match reached'; exit 203; }
shot stage3-match-prematch

clear_log; press_play 3; capture_log 'probe StartMatch -> stock MatchOver'; shot stage3-match-after-probe
clear_log; press_play 3; state="$(wait_state 'matchstats match' 30 || true)"; capture_log "full-time Play -> $state"
if [ "$state" = match ]; then clear_log; press_play 3; state="$(wait_state 'matchstats match' 30 || true)"; capture_log "full-time retry -> $state"; fi
[ "$state" = matchstats ] || { echo "Did not reach MatchStats: $state"; exit 204; }
shot stage3-matchstats

MY_MATCH_PLAYED=0; clear_log
for i in $(seq 1 24); do
  press_play 2; adb logcat -d -v brief > "$WORK/matchstats-progress.log" 2>/dev/null || true
  if grep -qiE 'MyMatchPlayed|CallFunc:[[:space:]]*PlayToDate|SetActive:[[:space:]]*message' "$WORK/matchstats-progress.log"; then MY_MATCH_PLAYED=1; break; fi
done
capture_log 'MatchStats -> MyMatchPlayed'; [ "$MY_MATCH_PLAYED" -eq 1 ] || { echo 'MyMatchPlayed not observed'; exit 205; }

PLAY_TO_DATE=0
for i in $(seq 1 8); do
  adb logcat -d -v brief > "$WORK/playtodate-progress.log" 2>/dev/null || true
  grep -qiE 'CallFunc:[[:space:]]*PlayToDate|PlayToDate' "$WORK/playtodate-progress.log" && PLAY_TO_DATE=1
  state="$(current_state)"; [ "$state" = leaguefixtures ] && break
  press_message_accept 3
done
capture_log 'MyMatchPlayed -> PlayToDate -> results'; state="$(current_state)"
if [ "$state" != leaguefixtures ]; then state="$(wait_state 'leaguefixtures league gamemenu matchreview message' 30 || true)"; fi
[ "$PLAY_TO_DATE" -eq 1 ] || { echo 'PlayToDate not observed'; exit 206; }

for step in $(seq 1 16); do
  case "$state" in leaguefixtures|league|matchreview) clear_log; press_play 3;; gamemenu) break;; message) clear_log; press_message_accept 3;; *) sleep 2;; esac
  state="$(wait_state 'league matchreview gamemenu message leaguefixtures' 25 || true)"; capture_log "post-match step $step -> $state"
done
[ "$state" = gamemenu ] || { echo "Did not return GameMenu: $state"; exit 207; }
sleep 2; capture_log 'post-match GameMenu'; dump_save post-match; shot stage3-post-match-gamemenu

adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game restart
open_slot0 restart
load_existing restart
dump_save post-restart; capture_log 'restart LoadCareer -> GameMenu'; shot stage3-post-restart

PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/verify_stage3_minimal.py \
  "$OUT/pre-match-MonkeyGame.xml" "$OUT/post-match-MonkeyGame.xml" "$OUT/post-restart-MonkeyGame.xml" \
  "$FLOW" "$OUT/STAGE3_MINIMAL_VERIFICATION.txt"
cat "$OUT/STAGE3_MINIMAL_VERIFICATION.txt"
