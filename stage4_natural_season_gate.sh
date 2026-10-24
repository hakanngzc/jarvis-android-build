#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage4-natural"
WORK="$RUNNER_TEMP/stage4-natural-work"
FLOW="$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
MIN_PROGRESS_DAYS="${MIN_PROGRESS_DAYS:-90}"
MIN_MATCH_CYCLES="${MIN_MATCH_CYCLES:-12}"
MIN_WALL_SECONDS="${MIN_WALL_SECONDS:-1200}"
MAX_MATCH_CYCLES="${MAX_MATCH_CYCLES:-60}"
MATCH_TIMEOUT_SECONDS="${MATCH_TIMEOUT_SECONDS:-360}"
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
: > "$FLOW"

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
    echo 'NSS-owned crash/ANR detected'; return 1
  fi
}
wait_log(){
  local pattern="$1" timeout_s="${2:-30}" label="${3:-wait}" i
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/wait-logcat.txt" 2>/dev/null || true
    if grep -qiE "$pattern" "$WORK/wait-logcat.txt"; then return 0; fi
    sleep 1
  done
  cp "$WORK/wait-logcat.txt" "$OUT/timeout-${label//[^A-Za-z0-9_-]/_}.txt" 2>/dev/null || true
  return 1
}
logical_xy(){
python3 - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:]); s=subprocess.check_output(['adb','shell','wm','size'],text=True)
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups()); scale=w/640.0; top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); adb shell input touchscreen tap "$x" "$y" </dev/null || true; sleep "${3:-2}"; }
swipe_logical(){
  local x1 y1 x2 y2; read -r x1 y1 < <(logical_xy "$1" "$2"); read -r x2 y2 < <(logical_xy "$3" "$4")
  adb shell input touchscreen swipe "$x1" "$y1" "$x2" "$y2" "${5:-350}" </dev/null || true
}
press_career(){ press_logical 471 541 "${1:-3}"; }
press_slot0(){ press_logical 332 324 "${1:-3}"; }
press_footer_ok(){ press_logical 536 880 "${1:-2}"; }
press_message_accept(){ press_logical 477 880 "${1:-2}"; }
press_play(){ press_logical 553 829 "${1:-2}"; }
shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }

start_game(){
  local tag="$1"; adb shell am force-stop "$PKG" >/dev/null 2>&1 || true; clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"
  sleep 2; capture_log "$tag mainmenu"
}
open_slot0(){
  local tag="$1"; clear_log; press_career 3
  wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 30 "$tag-saveslot"
  clear_log; press_slot0 3
}
load_existing(){
  local tag="$1"; sleep 2; adb logcat -d -v brief > "$WORK/$tag-load.txt" 2>/dev/null || true
  if ! grep -q 'LoadCareer saveslot: 0' "$WORK/$tag-load.txt"; then press_message_accept 3; fi
  wait_log 'LoadCareer saveslot: 0' 30 "$tag-loadcareer"
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 45 "$tag-gamemenu"
  capture_log "$tag load existing"
}
dump_save(){ local tag="$1"; adb shell cat "/data/data/$PKG/shared_prefs/MonkeyGame.xml" > "$OUT/$tag-MonkeyGame.xml"; grep -q monkeystate "$OUT/$tag-MonkeyGame.xml"; }
checkpoint(){
  local tag="$1"
  PYTHONPATH="$PWD/stage3_tools" python3 - "$OUT/$tag-MonkeyGame.xml" "$OUT/$tag.json" <<'PY'
import json,sys
from pathlib import Path
from stage2_checkpoint import extract_checkpoint,extract_monkeystate_from_prefs_xml
xml,out=map(Path,sys.argv[1:]); cp=extract_checkpoint(extract_monkeystate_from_prefs_xml(xml.read_text(encoding='utf-8')),0)
out.write_text(json.dumps(cp,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(cp,sort_keys=True))
PY
}
latest_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line; line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  line="${line,,}"
  case "$line" in
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;; *contract*) echo contract;; *webpage*) echo webpage;; *startransition*) echo startransition;; *skills*) echo skills;; *relationships*) echo relationships;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;; *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;; *) echo unknown;;
  esac
}

navigate_until_match(){
  local state=gamemenu step
  for step in $(seq 1 50); do
    fatal_check || return 1
    clear_log
    case "$state" in
      message|webpage|startransition) press_message_accept 2;;
      contract) press_footer_ok 2;;
      *) press_play 2;;
    esac
    sleep 1
    state="$(latest_state)"
    capture_log "navigate step $step -> $state"
    [ "$state" = match ] && return 0
    [ "$state" = unknown ] && { press_footer_ok 1; state="$(latest_state)"; }
  done
  return 1
}

natural_match_cycle(){
  local cycle="$1" start now elapsed state
  navigate_until_match || { shot "cycle-$cycle-no-match"; return 1; }
  shot "cycle-$cycle-match"
  clear_log; press_play 2
  start="$(date +%s)"
  while true; do
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/match-live.log" 2>/dev/null || true
    if grep -qiE 'SETTING ACTIVE:[[:space:]]*matchstats|SetActive:[[:space:]]*matchstats|Create Screen:[[:space:]]*matchstats' "$WORK/match-live.log"; then break; fi
    now="$(date +%s)"; elapsed=$((now-start))
    [ "$elapsed" -lt "$MATCH_TIMEOUT_SECONDS" ] || { cp "$WORK/match-live.log" "$OUT/cycle-$cycle-match-timeout.txt"; shot "cycle-$cycle-match-timeout"; return 1; }
    # Real live-match interaction only: ordinary touchscreen swipes/taps. No
    # match engine method is patched and no hidden simulate/debug branch is used.
    swipe_logical 320 700 320 250 420; sleep 1
    swipe_logical 260 690 460 280 380; sleep 1
    swipe_logical 380 690 180 280 380; sleep 1
    press_logical 320 600 1
  done
  elapsed=$(( $(date +%s)-start ))
  [ "$elapsed" -ge 30 ] || { echo "cycle $cycle completed implausibly fast: ${elapsed}s"; return 1; }
  capture_log "cycle $cycle natural Match -> MatchStats ${elapsed}s"
  shot "cycle-$cycle-matchstats"

  state=matchstats
  for _ in $(seq 1 40); do
    [ "$state" = gamemenu ] && break
    clear_log
    case "$state" in message|webpage|startransition) press_message_accept 2;; contract) press_footer_ok 2;; *) press_play 2;; esac
    state="$(latest_state)"; capture_log "cycle $cycle postmatch -> $state"
    [ "$state" = unknown ] && { press_footer_ok 1; state="$(latest_state)"; }
  done
  [ "$state" = gamemenu ] || return 1
  dump_save "cycle-$cycle"; checkpoint "cycle-$cycle"
}

# Exact stock source. Only onboarding overlays/trial are shortened to obtain a
# disposable fresh Career; the entire season progression and every live match
# below use the unmodified stock match/Career/season code.
curl -fL --retry 3 -A 'Mozilla/5.0' -e "$REFERER" "$URL" -o "$WORK/nss431.xapk"
echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c -
unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"; echo "$BASE_SHA  $BASE" | sha256sum -c -
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/trial-bootstrap-patch.txt"
python3 stage3_tools/patch_first_run_overlays.py "$WORK/base-career-unsigned.apk" "$WORK/base-natural-unsigned.apk" | tee "$OUT/overlay-patch.txt"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"; ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci -dname 'CN=NSS Stage4 Natural CI' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")"; "$ZIPALIGN" -f 4 "$src" "$tmp"; "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"; "$APKSIGNER" verify --verbose "$dst" >/dev/null; }
sign_one "$WORK/base-natural-unsigned.apk" "$WORK/signed/base-natural.apk"; sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"; sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"
adb install-multiple -r "$WORK/signed/base-natural.apk" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true; adb root >/dev/null 2>&1 || true; adb wait-for-device; sleep 2

start_game fresh; open_slot0 fresh
wait_log 'Create Screen:[[:space:]]*chooseclub|SETTING ACTIVE:[[:space:]]*chooseclub|SetActive:[[:space:]]*chooseclub' 30 chooseclub
for _ in 1 2 3 4; do adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true; grep -qiE 'choosenation' "$WORK/setup.txt" && break; press_footer_ok 2; fatal_check; done
wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
clear_log; press_footer_ok 2
wait_log 'LoadDataAndStartTrial|TrialDone|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|Create Screen:[[:space:]]*message' 30 career-message
for _ in 1 2 3 4 5 6; do press_message_accept 2; fatal_check; adb logcat -d -v brief > "$WORK/bootstrap.txt" 2>/dev/null || true; grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/bootstrap.txt" && break; done
wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 50 fresh-gamemenu
dump_save natural-baseline; checkpoint natural-baseline
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0

for cycle in $(seq 1 "$MAX_MATCH_CYCLES"); do
  natural_match_cycle "$cycle" || { echo "natural cycle $cycle failed"; exit 220; }
  CYCLES="$cycle"
  adb logcat -d -v brief >> "$FLOW" 2>/dev/null || true
  if grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp1' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp2' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp3' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp4' "$FLOW"; then
    SEASON_SEEN=1; break
  fi
done
[ "$SEASON_SEEN" -eq 1 ] || { echo "Natural season boundary not observed after $CYCLES cycles"; exit 221; }

dump_save post-season; checkpoint post-season
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game post-season-restart; open_slot0 post-season-restart; load_existing post-season-restart
dump_save post-season-restart; checkpoint post-season-restart
END_EPOCH="$(date +%s)"; WALL=$((END_EPOCH-START_EPOCH)); fatal_check

python3 - "$FLOW" "$OUT/natural-meta.json" "$CYCLES" "$WALL" "$MIN_MATCH_CYCLES" "$MIN_PROGRESS_DAYS" "$MIN_WALL_SECONDS" <<'PY'
import json,sys
flow,out,cycles,wall,mincycles,mindays,minwall=sys.argv[1:]
t=open(flow,encoding='utf-8',errors='replace').read()
data={'natural_match_cycles':int(cycles),'wall_seconds':int(wall),'minimum_match_cycles':int(mincycles),'minimum_progress_days':int(mindays),'minimum_wall_seconds':int(minwall),'nss_crash_or_anr':False}
for n in range(1,5): data[f'NewSeasonSetUp{n}']=f'NewSeasonSetUp{n}' in t
open(out,'w').write(json.dumps(data,indent=2,sort_keys=True)+'\n')
PY
python3 stage4_tools/verify_stage4_natural_season.py --base "$OUT/natural-baseline.json" --post "$OUT/post-season.json" --restart "$OUT/post-season-restart.json" --meta "$OUT/natural-meta.json" --out "$OUT/natural-verdict.json" | tee "$OUT/STAGE4_NATURAL_SEASON_RESULT.txt"
grep -q 'STAGE4_NATURAL_SEASON_PASS' "$OUT/STAGE4_NATURAL_SEASON_RESULT.txt"
echo 'STAGE4_NATURAL_SEASON_PASS'
