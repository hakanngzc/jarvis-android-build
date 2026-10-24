#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage2-residual"
WORK="$RUNNER_TEMP/stage2-residual-work"
FLOW="$OUT/STAGE2_RESIDUAL_RUNTIME_FLOW.log"
REMOTE_PREF="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
: > "$FLOW"

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

capture_log(){ local tag="$1"; { echo; echo "===== $tag ====="; adb logcat -d -v brief 2>/dev/null || true; } >> "$FLOW"; }
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
press_physical(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
press_logical(){ local x y; read -r x y < <(logical_xy "$1" "$2"); press_physical "$x" "$y" "${3:-2}"; }
press_career(){ press_logical 471 541 "${1:-3}"; }
press_slot0(){ press_logical 332 324 "${1:-3}"; }
press_footer_ok(){ press_logical 536 880 "${1:-2}"; }
press_message_accept(){ press_logical 477 880 "${1:-2}"; }
press_play(){ press_logical 553 829 "${1:-3}"; }
shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }

start_game(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"
  sleep 2
  capture_log "$tag mainmenu"
}
open_slot0(){
  local tag="$1"
  clear_log; press_career 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 30 "$tag-saveslot"
  shot "$tag-saveslot"
  clear_log; press_slot0 2
}
load_existing(){
  local tag="$1"
  adb logcat -d -v brief > "$WORK/$tag-load.txt" 2>/dev/null || true
  if ! grep -q 'LoadCareer saveslot: 0' "$WORK/$tag-load.txt"; then press_message_accept 2; fi
  wait_log 'LoadCareer saveslot: 0' 30 "$tag-loadcareer"
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 "$tag-gamemenu"
  capture_log "$tag load existing"
}
dump_save(){
  local tag="$1" xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$REMOTE_PREF" > "$xml"
  grep -q 'monkeystate' "$xml"
}
checkpoint(){
  local tag="$1"
  PYTHONPATH="$PWD/stage3_tools" python3 - "$OUT/${tag}-MonkeyGame.xml" "$OUT/${tag}.json" <<'PY'
import json,sys
from pathlib import Path
from stage2_checkpoint import extract_checkpoint,extract_monkeystate_from_prefs_xml
xml,out=map(Path,sys.argv[1:])
cp=extract_checkpoint(extract_monkeystate_from_prefs_xml(xml.read_text(encoding='utf-8')),0)
out.write_text(json.dumps(cp,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(cp,sort_keys=True))
PY
}
restore_baseline(){
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb push "$WORK/baseline.xml" /data/local/tmp/nss-baseline.xml >/dev/null
  adb shell "cat /data/local/tmp/nss-baseline.xml > '$REMOTE_PREF'" >/dev/null
  adb shell rm -f /data/local/tmp/nss-baseline.xml >/dev/null 2>&1 || true
}

curl -fL --retry 3 -A 'Mozilla/5.0' -e "$REFERER" "$URL" -o "$WORK/nss431.xapk"
echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c -
unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$BASE_SHA  $BASE" | sha256sum -c -
unzip -p "$BASE" assets/monkey/MyData/v2025/Clubs.txt > "$WORK/Clubs.txt"

PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/trial-bootstrap-patch.txt"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci -dname 'CN=NSS Stage2 Residual CI' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")"; "$ZIPALIGN" -f 4 "$src" "$tmp"; "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"; "$APKSIGNER" verify --verbose "$dst" >/dev/null; }
sign_one "$WORK/base-career-unsigned.apk" "$WORK/signed/base-career.apk"
sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"
sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"
install_base(){ adb install-multiple -r "$1" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" >/dev/null; }

install_base "$WORK/signed/base-career.apk"
adb shell pm clear "$PKG" >/dev/null || true
adb root >/dev/null 2>&1 || true; adb wait-for-device; sleep 2

# Fresh disposable Career bootstrap. This only shortens onboarding; all residual
# mutation writers, save, process restart and load paths remain stock.
start_game fresh
open_slot0 fresh
wait_log 'Create Screen:[[:space:]]*chooseclub|SETTING ACTIVE:[[:space:]]*chooseclub|SetActive:[[:space:]]*chooseclub' 30 chooseclub
for _ in 1 2 3 4; do adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true; grep -qiE 'choosenation' "$WORK/setup.txt" && break; press_footer_ok 2; fatal_check; done
wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
clear_log; press_footer_ok 2
wait_log 'LoadDataAndStartTrial|TrialDone|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|Create Screen:[[:space:]]*message' 30 career-message
for _ in 1 2 3 4 5 6; do
  press_message_accept 2; fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/save-progress.txt" && break
done
wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 50 fresh-gamemenu
dump_save baseline; checkpoint baseline
cp "$OUT/baseline-MonkeyGame.xml" "$WORK/baseline.xml"

read -r BASE_CLUB BASE_NATION < <(python3 - "$OUT/baseline.json" <<'PY'
import json,sys
x=json.load(open(sys.argv[1])); print(x['clubid'],x['clubnationid'])
PY
)
DEST_CLUB="$(python3 - "$WORK/Clubs.txt" "$BASE_CLUB" "$BASE_NATION" <<'PY'
import sys
p,current,nation=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
rows=[]
with open(p,encoding='utf-8-sig',errors='replace') as f:
    header=f.readline().rstrip('\r\n').split('\t')
    if len(header)<16:
        header=f.readline().rstrip('\r\n').split()
    # Restart if the first line was actually a whitespace header.
with open(p,encoding='utf-8-sig',errors='replace') as f:
    lines=f.read().splitlines()
head=lines[0].split('\t')
if len(head)<16: head=lines[0].split()
idx={n:i for i,n in enumerate(head)}
def parts(line):
    v=line.split('\t'); return v if len(v)>=16 else line.split()
parsed=[]
for line in lines[1:]:
    if not line.strip() or line.lstrip().startswith(('#','//',';')): continue
    v=parts(line)
    if len(v)<16 or not v[0].lstrip('-').isdigit(): continue
    parsed.append(v)
cur=next(v for v in parsed if int(v[idx['id']])==current)
league=int(cur[idx['leagueid']])
for v in parsed:
    cid=int(v[idx['id']]); nid=int(v[idx['nationid']]); lid=int(v[idx['leagueid']]); b=int(v[idx['bteamof']])
    if cid!=current and nid==nation and lid==league and b==0:
        print(cid); break
else: raise SystemExit('no same-nation/same-league transfer destination')
PY
)"
echo "BASE_CLUB=$BASE_CLUB BASE_NATION=$BASE_NATION DEST_CLUB=$DEST_CLUB" | tee "$OUT/transfer-destination.txt"

build_probe(){
  local scenario="$1" dest="${2:-}" out="$WORK/base-$scenario-unsigned.apk"
  args=(stage2_residual_tools/patch_stage2_residual_probe.py "$WORK/base-career-unsigned.apk" "$out" --scenario "$scenario")
  [ -n "$dest" ] && args+=(--destination-club-id "$dest")
  PYTHONPATH="$PWD/stage3_tools" python3 "${args[@]}" | tee "$OUT/$scenario-probe.txt"
  sign_one "$out" "$WORK/signed/base-$scenario.apk"
}

build_probe accept
build_probe reject
build_probe transfer "$DEST_CLUB"
build_probe retire

run_scenario(){
  local scenario="$1" dest="${2:-}"
  echo "=== scenario $scenario ===" | tee -a "$FLOW"
  restore_baseline
  install_base "$WORK/signed/base-$scenario.apk"
  start_game "$scenario"
  open_slot0 "$scenario"
  load_existing "$scenario"
  dump_save "$scenario-pre"; checkpoint "$scenario-pre"

  clear_log; press_play 4; fatal_check; capture_log "$scenario mutation trigger"
  sleep 2
  dump_save "$scenario-post"; checkpoint "$scenario-post"
  shot "$scenario-post"

  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  start_game "$scenario-restart"
  open_slot0 "$scenario-restart"

  if [ "$scenario" = retire ]; then
    # A retired slot may remain on SaveSlot instead of entering GameMenu. Opening
    # SaveSlot is still the stock runtime metadata reload boundary; raw Career
    # state is then checked and a second stock ButtonPlay no-op is attempted only
    # if LoadCareer remains available.
    sleep 3; capture_log 'retire post-restart SaveSlot metadata'; shot retire-post-restart-saveslot
    adb logcat -d -v brief > "$WORK/retire-restart-state.txt" 2>/dev/null || true
    if grep -q 'LoadCareer saveslot: 0' "$WORK/retire-restart-state.txt"; then
      wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 30 retire-reload-gamemenu || true
    fi
  else
    load_existing "$scenario-restart"
  fi
  dump_save "$scenario-post-restart"; checkpoint "$scenario-post-restart"

  extra=()
  if [ "$scenario" = transfer ]; then extra+=(--destination-club-id "$dest"); fi
  if [ "$scenario" = retire ]; then
    # If runtime still allows the retired Career to be loaded, invoke the exact
    # patched PlayMatches trigger again. GameMenu Play first opens LeagueFixtures;
    # the second Play reaches the authoritative stock Retirement.m_ButtonPlay.
    # Because m_retired was restored nonzero, the second writer execution must
    # leave the durable Career checkpoint unchanged.
    if grep -q 'LoadCareer saveslot: 0' "$WORK/retire-restart-state.txt"; then
      clear_log
      press_play 3
      wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 retire-second-leaguefixtures
      fatal_check
      capture_log 'retire second probe GameMenu -> LeagueFixtures'
      clear_log
      press_play 3
      sleep 3
      fatal_check
      capture_log 'retire second stock retirement writer no-op'
      dump_save retire-second-after-reload
      checkpoint retire-second-after-reload
    else
      cp "$OUT/retire-post-restart.json" "$OUT/retire-second-after-reload.json"
    fi
    extra+=(--second-after-reload "$OUT/retire-second-after-reload.json")
  fi

  python3 stage2_residual_tools/verify_stage2_residual.py \
    --scenario "$scenario" --base "$OUT/baseline.json" \
    --post "$OUT/$scenario-post.json" --restart "$OUT/$scenario-post-restart.json" \
    "${extra[@]}" --out "$OUT/$scenario-verdict.json" | tee "$OUT/$scenario-verdict.txt"
}

run_scenario accept
run_scenario reject
run_scenario transfer "$DEST_CLUB"
run_scenario retire

grep -q 'STAGE2_ACCEPT_RESTART_RELOAD_PASS' "$OUT/accept-verdict.txt"
grep -q 'STAGE2_REJECT_RESTART_RELOAD_PASS' "$OUT/reject-verdict.txt"
grep -q 'STAGE2_TRANSFER_RESTART_RELOAD_PASS' "$OUT/transfer-verdict.txt"
grep -q 'STAGE2_RETIRE_RESTART_RELOAD_PASS' "$OUT/retire-verdict.txt"
fatal_check

echo 'STAGE2_RESIDUAL_RUNTIME_PASS' | tee "$OUT/STAGE2_RESIDUAL_RUNTIME_RESULT.txt"
