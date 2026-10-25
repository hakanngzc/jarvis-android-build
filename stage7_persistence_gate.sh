#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage7-persistence"
WORK="$RUNNER_TEMP/stage7-work"
FLOW="$OUT/STAGE7_RUNTIME_FLOW.log"
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
: > "$FLOW"

ADB_BIN="$(command -v adb)"
adb(){
  { printf '%q ' "$ADB_BIN" "$@"; printf '\n'; } > "$OUT/last-adb-command.txt"
  command timeout --signal=TERM --kill-after=5s 45s "$ADB_BIN" "$@"
}

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

capture_log(){ local label="$1"; { echo; echo "===== $label ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"; }
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }
fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
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
logical_xy(){
python3 - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:])
s=subprocess.check_output(['adb','shell','wm','size'],text=True,timeout=15)
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups())
scale=w/640.0
top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_physical(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
press_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); press_physical "$x" "$y" "${3:-2}"; }
press_career(){
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r')"
  case "$size" in
    *1080x2280*) adb shell input touchscreen tap 795 1399 </dev/null || true; sleep "${1:-3}" ;;
    *) echo "Unsupported Stage7 MainMenu geometry: $size" >&2; return 1 ;;
  esac
}
press_slot0(){ press_logical 332 324 "${1:-3}"; }
press_footer_ok(){ press_logical 536 880 "${1:-2}"; }
press_message_accept(){ press_logical 477 880 "${1:-2}"; }
press_play(){
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r')"
  case "$size" in
    *1080x2280*) adb shell input touchscreen tap 935 1850 </dev/null || true; sleep "${1:-3}" ;;
    *) echo "Unsupported Stage7 Play geometry: $size" >&2; return 1 ;;
  esac
}
shot(){ adb exec-out screencap -p > "$OUT/$1.png" || true; }

start_game(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"
  local rendered=0 ready_i bytes
  for ready_i in $(seq 1 45); do
    adb exec-out screencap -p > "$WORK/render-probe.png" 2>/dev/null || true
    bytes="$(wc -c < "$WORK/render-probe.png" 2>/dev/null || echo 0)"
    if [ "${bytes:-0}" -gt 30000 ]; then
      cp "$WORK/render-probe.png" "$OUT/${tag}-render-ready.png" || true
      rendered=1
      break
    fi
    sleep 1
  done
  [ "$rendered" -eq 1 ] || { echo 'Rendered frame did not become ready'; return 1; }
  test -n "$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  capture_log "$tag mainmenu"
  shot "$tag-mainmenu"
}
open_slot0(){
  local tag="$1" attempt reached=0
  for attempt in 1 2 3; do
    clear_log
    press_career 2
    if wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 6 "$tag-saveslot-attempt-$attempt"; then
      reached=1; break
    fi
  done
  [ "$reached" -eq 1 ] || return 1
  local slot_attempt slot_hit=0
  for slot_attempt in 1 2 3; do
    clear_log
    press_slot0 3
    adb logcat -d -v brief > "$WORK/$tag-slot0-attempt-$slot_attempt.txt" 2>/dev/null || true
    if grep -q 'HitGadget: saveslot.btn_Slot0' "$WORK/$tag-slot0-attempt-$slot_attempt.txt"; then
      slot_hit=1; break
    fi
    fatal_check || return 1
  done
  [ "$slot_hit" -eq 1 ] || return 1
}
load_existing(){
  local tag="$1"
  sleep 2
  adb logcat -d -v brief > "$WORK/$tag-load.txt" 2>/dev/null || true
  if ! grep -q 'LoadCareer saveslot: 0' "$WORK/$tag-load.txt"; then press_message_accept 3; fi
  wait_log 'LoadCareer saveslot:[[:space:]]*0' 30 "$tag-loadcareer"
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 "$tag-gamemenu"
  capture_log "$tag load existing"
}
dump_save(){
  local tag="$1" remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml" xml="$OUT/${1}-MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || true
  grep -q 'monkeystate' "$xml" || { echo "Could not read $remote for $tag"; return 1; }
  sha256sum "$xml" >> "$OUT/save-sha256.txt"
}

# Exact public NSS 4.31 source.
curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$WORK/nss431.xapk"
echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c -
unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$BASE_SHA  $BASE" | sha256sum -c -

# Reuse the proven TEST-ONLY fresh-Career/trial shortcut. Stock persistence remains untouched.
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/career-trial-patch.txt"
python3 stage3_tools/patch_first_run_overlays.py "$WORK/base-career-unsigned.apk" "$WORK/base-career-overlay-unsigned.apk" | tee "$OUT/first-run-overlay-patch.txt"
mv "$WORK/base-career-overlay-unsigned.apk" "$WORK/base-career-unsigned.apk"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci -dname 'CN=NSS Stage7 CI' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1"
  local dst="$2"
  local tmp="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$tmp"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-career-unsigned.apk" "$WORK/signed/base-career.apk"
sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"
sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"
install_base(){ adb install-multiple -r "$1" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" >/dev/null; }
install_base "$WORK/signed/base-career.apk"
adb shell pm clear "$PKG" >/dev/null || true
adb root >/dev/null 2>&1 || true
adb wait-for-device
sleep 2

# Create one fresh durable Career using the already-proven Stage3 path.
start_game fresh
open_slot0 fresh
wait_log 'Create Screen:[[:space:]]*chooseclub|SETTING ACTIVE:[[:space:]]*chooseclub|SetActive:[[:space:]]*chooseclub' 30 chooseclub
for _ in 1 2 3 4; do
  adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true
  grep -qiE 'choosenation' "$WORK/setup.txt" && break
  press_footer_ok 2
  fatal_check
done
wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
clear_log
press_footer_ok 2
wait_log 'LoadDataAndStartTrial|TrialDone|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|Create Screen:[[:space:]]*message' 30 'career message'
for _ in 1 2 3 4; do
  press_message_accept 2
  fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/save-progress.txt" && break
done
wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 fresh-gamemenu || true
capture_log 'fresh Career saved'

# Install Stage7 probe update with the same test signer. Do NOT clear app data.
# Install Stage7 probe update
PYTHONPATH="$PWD" python3 stage7_tools/patch_stage7_persistence_probe.py "$WORK/base-career-unsigned.apk" "$WORK/base-stage7-unsigned.apk" | tee "$OUT/stage7-probe-patch.txt"
sign_one "$WORK/base-stage7-unsigned.apk" "$WORK/signed/base-stage7.apk"
install_base "$WORK/signed/base-stage7.apk"
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true

start_game stage7
open_slot0 stage7
load_existing stage7
dump_save pre-save

# GameMenu -> LeagueFixtures -> TEST-ONLY g_GSPlayerPlayMatches sentinel trigger.
clear_log
press_play 4
wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 leaguefixtures
capture_log 'GameMenu -> LeagueFixtures'
clear_log
press_play 3
wait_log 'SAVE CAREER|SaveCareer|SaveState' 30 stage7-stock-save
fatal_check
capture_log 'Stage7 sentinels -> stock p_SaveCareer'
sleep 2
dump_save post-save

# Process death + stock slot reload. App data remains intact.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game reload
wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 reload-loadcareer
wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 reload-gamemenu
fatal_check
sleep 2
dump_save post-restart
capture_log 'Stage7 after process death / stock reload'

PYTHONPATH="$PWD" python3 stage7_tools/verify_stage7_persistence_runtime.py \
  "$OUT/pre-save-MonkeyGame.xml" \
  "$OUT/post-save-MonkeyGame.xml" \
  "$OUT/post-restart-MonkeyGame.xml" \
  "$FLOW" | tee "$OUT/STAGE7_PERSISTENCE_GATE.txt"
grep -q 'STAGE7_PERSISTENCE_RUNTIME_PASS' "$OUT/STAGE7_PERSISTENCE_GATE.txt"
echo 'STAGE7_PERSISTENCE_FULL_RUNTIME_PASS'
