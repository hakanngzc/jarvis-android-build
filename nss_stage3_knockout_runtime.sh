#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
case "$MODE" in
  extra-time|shootout) ;;
  *) echo 'usage: bash nss_stage3_knockout_runtime.sh extra-time|shootout' >&2; exit 2 ;;
esac

PKG=com.newstargames.newstarsoccer
WORK="$RUNNER_TEMP/nss-stage3-knockout-$MODE"
OUT="$WORK/out"
ROOT="$WORK/xapk"
SIGNED="$WORK/signed"
XAPK="$WORK/stock.xapk"
mkdir -p "$ROOT" "$SIGNED" "$OUT"

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
EXPECTED_XAPK='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
EXPECTED_BASE='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$XAPK"
echo "$EXPECTED_XAPK  $XAPK" | sha256sum -c -
unzip -q "$XAPK" -d "$ROOT"
echo "$EXPECTED_BASE  $ROOT/com.newstargames.newstarsoccer.apk" | sha256sum -c -

# Reuse the same startup shortcuts already proven by the successful stock Career
# probe. These do not touch the knockout methods under test.
python3 - "$ROOT/com.newstargames.newstarsoccer.apk" "$WORK/base-ui-probe.apk" <<'PY'
import sys, zipfile
src,dst=sys.argv[1:]
repl={
 'assets/monkey/NewGUI/Screens/onboardingmain.uih': b'Rect:(0,0,0,0)\n    SetTweak(FirstPlayLocal,FirstPlayIncrement,4)\n',
 'assets/monkey/NewGUI/Screens/consent.uih': b'Macro:(M_Consent_Panel)\nEndM\nMacro:(M_Consent_Panel_ATT)\nEndM\n',
}
seen=set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w') as zout:
    for info in zin.infolist():
        data=zin.read(info.filename)
        if info.filename in repl:
            data=repl[info.filename]; seen.add(info.filename)
        zi=zipfile.ZipInfo(info.filename,info.date_time)
        zi.compress_type=info.compress_type; zi.comment=info.comment; zi.extra=info.extra
        zi.internal_attr=info.internal_attr; zi.external_attr=info.external_attr
        zi.create_system=info.create_system; zi.flag_bits=info.flag_bits
        zout.writestr(zi,data)
missing=set(repl)-seen
if missing: raise SystemExit(f'missing UI entries: {sorted(missing)}')
PY
python3 tools/patch_cloud_startup_bypass_for_persistence_test.py "$WORK/base-ui-probe.apk" "$WORK/base-cloud-probe.apk"
python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe.apk"
python3 stage3/patch_stage3_knockout_apk.py "$MODE" "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \
  --evidence "$OUT/STAGE3_KNOCKOUT_APK_PATCH.json" | tee "$OUT/STAGE3_KNOCKOUT_APK_PATCH.txt"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android \
  -alias ci -dname 'CN=NSS Stage3 Public Knockout Probe' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1

sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --min-sdk-version 24 --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-knockout-probe.apk" "$SIGNED/base.apk"
sign_one "$ROOT/config.tr.apk" "$SIGNED/config.tr.apk"
sign_one "$ROOT/config.xxhdpi.apk" "$SIGNED/config.xxhdpi.apk"
adb install-multiple -r "$SIGNED/base.apk" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true

fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
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
shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }
press_physical(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
logical_xy(){
python3 - "$1" "$2" <<'PY'
import re,subprocess,sys
x,y=map(float,sys.argv[1:])
s=subprocess.check_output(['adb','shell','wm','size'],text=True)
w,h=map(int,re.search(r'(\d+)x(\d+)',s).groups())
scale=w/640.0; top=(h-960*scale)/2.0
print(round(x*scale),round(top+y*scale))
PY
}
press_footer_ok(){ local x y; read -r x y < <(logical_xy 536 880); press_physical "$x" "$y" "${1:-2}"; }
press_message_accept(){ local x y; read -r x y < <(logical_xy 477 880); press_physical "$x" "$y" "${1:-2}"; }
press_play(){ local x y; read -r x y < <(logical_xy 553 829); press_physical "$x" "$y" "${1:-2}"; }
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }

start_menu(){
  local i last bytes png="$WORK/menu-render.png"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  for i in $(seq 1 75); do
    sleep 1
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/start.log" 2>/dev/null || true
    last="$(grep -Ei 'SetActive:[[:space:]]*[A-Za-z0-9_]+' "$WORK/start.log" | tail -1 || true)"
    if grep -qiE 'SetActive:[[:space:]]*mainmenu' <<<"$last"; then
      adb exec-out screencap -p > "$png" 2>/dev/null || true
      bytes="$(wc -c < "$png" 2>/dev/null || echo 0)"
      if [ "$bytes" -gt 200000 ]; then
        cp "$png" "$OUT/stock-mainmenu-rendered.png"
        echo "Stock MainMenu rendered after ${i}s (${bytes} bytes)"
        return 0
      fi
    fi
  done
  cp "$WORK/start.log" "$OUT/start-menu-timeout.log" 2>/dev/null || true
  shot start-menu-timeout
  return 1
}

find_slot0_target(){
python3 - "$1" "$2" <<'PY'
from PIL import Image
import sys
im=Image.open(sys.argv[1]).convert('RGB'); w,h=im.size
palette=[(246,233,210),(217,229,227),(255,249,237)]
def near(p,t,tol=42): return max(abs(p[i]-t[i]) for i in range(3))<=tol
rows=[]
for y in range(int(h*.14),int(h*.84),2):
    hits=0; total=0
    for x in range(int(w*.05),int(w*.95),4):
        total+=1; p=im.getpixel((x,y))
        if any(near(p,t) for t in palette): hits+=1
    if hits/max(1,total)>=.20: rows.append(y)
if not rows: raise SystemExit('SaveSlot card rows not detected')
groups=[]; start=prev=rows[0]
for y in rows[1:]:
    if y-prev<=4: prev=y
    else: groups.append((start,prev)); start=prev=y
groups.append((start,prev))
groups=[g for g in groups if g[1]-g[0]>=h*.035 and g[0]>=h*.16]
if not groups: raise SystemExit(f'SaveSlot visual fingerprint incomplete: {groups}')
y0,y1=groups[0]
x=w//2; y=round(y0+(y1-y0)*.70)
open(sys.argv[2],'w').write(f'{x} {y}\n')
print('slot0_target',x,y,'bands',groups)
PY
}

current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local line
  line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  case "${line,,}" in
    *matchreview*) echo matchreview ;;
    *matchstats*) echo matchstats ;;
    *leaguefixtures*) echo leaguefixtures ;;
    *gamemenu*) echo gamemenu ;;
    *message*) echo message ;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match ;;
    *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league ;;
    *) echo unknown ;;
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
  echo unknown
  return 1
}

# Fresh disposable Career.
start_menu
adb shell wm size > "$OUT/wm-size.txt"
adb shell wm density > "$OUT/wm-density.txt"
clear_log
press_physical 810 1450 2
wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot
shot saveslot
find_slot0_target "$OUT/saveslot.png" "$WORK/slot0.txt"
read -r SLOT_X SLOT_Y < "$WORK/slot0.txt"
clear_log
press_physical "$SLOT_X" "$SLOT_Y" 3
wait_log 'Create Screen:[[:space:]]*chooseclub|Create Screen:chooseclub' 25 chooseclub

for _ in 1 2 3 4; do
  adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true
  grep -qiE 'Create Screen:[[:space:]]*choosenation|Create Screen:choosenation' "$WORK/setup.txt" && break
  press_footer_ok 2
  fatal_check
done
wait_log 'Create Screen:[[:space:]]*choosenation|Create Screen:choosenation' 25 choosenation
clear_log
press_footer_ok 2
wait_log 'CallFunc:[[:space:]]*LoadDataAndStartTrial|CallFunc:[[:space:]]*TrialDone|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|Create Screen:[[:space:]]*message|Create Screen:message' 25 'career message'
for _ in 1 2 3 4 5; do
  press_message_accept 2
  fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/save-progress.txt"; then break; fi
done
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 35 gamemenu
shot career-gamemenu

# Drive normal stock UI to the next playable match.
state=gamemenu
MATCH_REACHED=0
for step in $(seq 1 32); do
  clear_log
  case "$state" in
    gamemenu|leaguefixtures|league) press_play 3 ;;
    message) press_message_accept 3 ;;
    match) MATCH_REACHED=1; break ;;
    *) sleep 2 ;;
  esac
  state="$(wait_state 'match message leaguefixtures league gamemenu' 25 || true)"
  {
    echo "step=$step state=$state"
    adb logcat -d -v brief 2>/dev/null || true
  } >> "$OUT/navigation.log"
  if [ "$state" = match ]; then MATCH_REACHED=1; break; fi
done
[ "$MATCH_REACHED" -eq 1 ] || { echo 'No playable Career match reached'; shot no-match; exit 203; }
shot knockout-match-prematch

# Invoke only the patched StartMatch boundary. All downstream knockout methods
# are stock and their hashes are already recorded in STAGE3_KNOCKOUT_APK_PATCH.json.
clear_log
press_play 2
sleep 1
shot "knockout-$MODE-t1"
sleep 2
shot "knockout-$MODE-t3"
adb logcat -d -v threadtime > "$OUT/knockout-$MODE-after-start.log" 2>/dev/null || true
fatal_check

if [ "$MODE" = shootout ]; then
  clear_log
  press_play 2
  sleep 1
  shot knockout-shootout-after-second-play-t1
  sleep 2
  shot knockout-shootout-after-second-play-t3
  adb logcat -d -v threadtime > "$OUT/knockout-shootout-after-second-play.log" 2>/dev/null || true
  fatal_check
fi

python3 - "$MODE" "$OUT/STAGE3_KNOCKOUT_RUNTIME_RESULT.json" <<'PY'
import json,sys
mode,out=sys.argv[1:]
record={
  'schema':1,
  'mode':mode,
  'source':'APKPure verified public NSS 4.31 versionCode 137',
  'source_xapk_sha256':'afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e',
  'automation':'ANDROID_EMULATOR_NO_HUMAN_INPUT',
  'probe_boundary':'c_TMatch.m_StartMatch only',
  'stock_knockout_methods_untouched':True,
  'screenshots_captured':True,
  'test_only_never_ship':True,
  'verdict':'STAGE3_KNOCKOUT_RUNTIME_CAPTURED_PENDING_VISUAL_REVIEW',
}
open(out,'w',encoding='utf-8').write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record,indent=2,sort_keys=True))
PY

echo "ARTIFACT_DIR=$OUT"
echo 'VERDICT=STAGE3_KNOCKOUT_RUNTIME_CAPTURED_PENDING_VISUAL_REVIEW'
