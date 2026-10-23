#!/usr/bin/env bash
set -euo pipefail

PKG='com.newstargames.newstarsoccer'
PREF='/data/user/0/com.newstargames.newstarsoccer/shared_prefs/MonkeyGame.xml'
WORK="$RUNNER_TEMP/nss-stage5-save-compat"
OUT="$WORK/out"
ROOT="$WORK/xapk"
SIGNED="$WORK/signed"
XAPK="$WORK/stock.xapk"
mkdir -p "$ROOT" "$SIGNED" "$OUT"

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
EXPECTED_XAPK='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
EXPECTED_BASE='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

curl -fL --retry 3 \
  -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' \
  -e "$REFERER" "$URL" -o "$XAPK"
echo "$EXPECTED_XAPK  $XAPK" | sha256sum -c -
unzip -q "$XAPK" -d "$ROOT"
echo "$EXPECTED_BASE  $ROOT/com.newstargames.newstarsoccer.apk" | sha256sum -c -

# Test-only startup friction removal. The stock serializer, SaveCareer, LoadCareer,
# football ID readers and football tables are untouched in Build A.
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
python3 tools/patch_cloud_startup_bypass_for_persistence_test.py \
  "$WORK/base-ui-probe.apk" "$WORK/base-cloud-probe.apk"
python3 tools/patch_trial_skip_for_persistence_test.py \
  "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe.apk"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android \
  -alias ci -dname 'CN=NSS Stage5 Save Compatibility Probe' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1

sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci \
    --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --min-sdk-version 24 --verbose "$dst" >/dev/null
}
install_with_base(){
  local base="$1"
  adb install-multiple -r "$base" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
}

sign_one "$WORK/base-career-probe.apk" "$SIGNED/base-a.apk"
sign_one "$ROOT/config.tr.apk" "$SIGNED/config.tr.apk"
sign_one "$ROOT/config.xxhdpi.apk" "$SIGNED/config.xxhdpi.apk"
install_with_base "$SIGNED/base-a.apk"
adb shell pm clear "$PKG" >/dev/null || true
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true

fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected' >&2
    return 1
  fi
}
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }
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
  echo "Timed out waiting for $label" >&2
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

start_menu(){
  local tag="$1" i last bytes png="$OUT/${tag}-mainmenu.png"
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
        echo "Stock MainMenu rendered after ${i}s (${bytes} bytes)"
        return 0
      fi
    fi
  done
  cp "$WORK/start.log" "$OUT/${tag}-start-timeout.log" 2>/dev/null || true
  return 1
}

open_slot0(){
  local tag="$1" main="$OUT/${tag}-mainmenu.png" slot="$OUT/${tag}-saveslot.png"
  start_menu "$tag"
  python3 knockout_v6/pick_mainmenu_play.py "$main" "$WORK/${tag}-play.txt"
  read -r mx my < "$WORK/${tag}-play.txt"
  clear_log
  press_physical "$mx" "$my" 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot
  shot "${tag}-saveslot"
  python3 stage3/pick_saveslot.py "$slot" "$WORK/${tag}-slot0.txt"
  read -r sx sy < "$WORK/${tag}-slot0.txt"
  clear_log
  press_physical "$sx" "$sy" 3
}

# Fresh disposable stock Career and real stock save.
open_slot0 fresh
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
shot fresh-career-gamemenu
adb logcat -d -v threadtime > "$OUT/fresh-career-save.log" 2>/dev/null || true
grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$OUT/fresh-career-save.log" || {
  echo 'Stock save evidence missing' >&2; exit 41;
}

# Root is available on the pinned GMS-free AOSP emulator and lets us compare the
# exact app-private SharedPreferences bytes without modifying them.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb root | tee "$OUT/adb-root.txt"
adb wait-for-device
adb shell id | tee "$OUT/adb-root-id.txt"
grep -q 'uid=0(root)' "$OUT/adb-root-id.txt" || { echo 'adb root unavailable' >&2; exit 42; }
adb shell test -s "$PREF" || { echo 'MonkeyGame.xml missing after stock save' >&2; exit 43; }
adb exec-out cat "$PREF" > "$OUT/save-before-update.xml"
grep -q '\.monkeystate' "$OUT/save-before-update.xml" || { echo '.monkeystate key missing' >&2; exit 44; }
SAVE_SHA_BEFORE="$(sha256sum "$OUT/save-before-update.xml" | awk '{print $1}')"
echo "SAVE_SHA_BEFORE=$SAVE_SHA_BEFORE"

# NAME_ONLY_UPDATE_BEGIN
# Build B changes every numeric v2025 club/nation/competition display name by
# one suffix character. IDs, row ordering and persistent reference columns must
# remain identical. The same signing key is used and app data is not cleared.
python3 - "$WORK/base-career-probe.apk" "$WORK/base-name-update-unsigned.apk" "$OUT/STAGE5_NAME_PATCH_REPORT.json" <<'PY'
import json,sys
from pathlib import Path
from stage5.name_only_patch import patch_apk_bytes
src,dst,report=sys.argv[1:]
patched, rec = patch_apk_bytes(Path(src).read_bytes(), suffix='~')
Path(dst).write_bytes(patched)
Path(report).write_text(json.dumps(rec,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(rec,sort_keys=True))
if not rec['identity_contract_preserved'] or not rec['persistent_references_preserved']:
    raise SystemExit('name-only identity contract failed')
if rec['changed_total'] <= 0:
    raise SystemExit('no football names changed')
PY

python3 - "$WORK/base-career-probe.apk" "$WORK/base-name-update-unsigned.apk" "$OUT/STAGE5_APK_DIFF.json" <<'PY'
import hashlib,json,sys,zipfile
from pathlib import Path
old,new,out=sys.argv[1:]
allowed={
 'assets/monkey/MyData/v2025/Clubs.txt',
 'assets/monkey/MyData/v2025/Nations.txt',
 'assets/monkey/MyData/v2025/Competitions.txt',
}
def hashes(path):
    with zipfile.ZipFile(path) as z:
        return {n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()}
a=hashes(old); b=hashes(new)
if set(a)!=set(b): raise SystemExit('APK entry set changed')
changed=sorted(n for n in a if a[n]!=b[n])
if set(changed)!=allowed: raise SystemExit(f'unexpected changed APK entries: {changed}')
classes={n:a[n] for n in a if n.endswith('.dex')}
if any(a[n]!=b[n] for n in classes): raise SystemExit('DEX changed in name-only update')
rec={'changed_entries':changed,'changed_entries_exact':True,'dex_hashes_unchanged':classes}
Path(out).write_text(json.dumps(rec,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(rec,sort_keys=True))
PY

sign_one "$WORK/base-name-update-unsigned.apk" "$SIGNED/base-b-name-update.apk"
install_with_base "$SIGNED/base-b-name-update.apk"

# Exact old save bytes must survive the same-signed package update before launch.
adb wait-for-device
adb shell test -s "$PREF" || { echo 'MonkeyGame.xml missing after update' >&2; exit 45; }
adb exec-out cat "$PREF" > "$OUT/save-after-update-before-launch.xml"
SAVE_SHA_AFTER_UPDATE="$(sha256sum "$OUT/save-after-update-before-launch.xml" | awk '{print $1}')"
echo "SAVE_SHA_AFTER_UPDATE=$SAVE_SHA_AFTER_UPDATE"
[ "$SAVE_SHA_BEFORE" = "$SAVE_SHA_AFTER_UPDATE" ] || {
  echo 'Raw save changed during name-only package update' >&2; exit 46;
}

# The unchanged old save must still resolve through stock LoadCareer under the
# renamed static data and reach the real Career hub.
open_slot0 name-update
sleep 2
adb logcat -d -v brief > "$WORK/name-update-load-progress.txt" 2>/dev/null || true
if ! grep -qiE 'LoadCareer saveslot:[[:space:]]*0' "$WORK/name-update-load-progress.txt"; then
  press_message_accept 3
fi
wait_log 'LoadCareer saveslot:[[:space:]]*0' 30 old-save-load
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 35 old-save-gamemenu
shot name-update-loaded-gamemenu
adb logcat -d -v threadtime > "$OUT/name-update-load.log" 2>/dev/null || true
fatal_check

python3 - "$OUT/STAGE5_NAME_PATCH_REPORT.json" "$OUT/STAGE5_APK_DIFF.json" \
  "$SAVE_SHA_BEFORE" "$SAVE_SHA_AFTER_UPDATE" "$OUT/STAGE5_SAVE_COMPAT_RESULT.json" <<'PY'
import json,sys
from pathlib import Path
patch_path,diff_path,before,after,out=sys.argv[1:]
patch=json.loads(Path(patch_path).read_text())
diff=json.loads(Path(diff_path).read_text())
rec={
 'schema':1,
 'source':'APKPure verified public NSS 4.31 versionCode 137',
 'source_xapk_sha256':'afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e',
 'source_base_sha256':'46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4',
 'android_api':29,
 'test_only_startup_trial_shortcuts':True,
 'stock_save_load_methods_replaced':False,
 'name_patch':patch,
 'apk_diff':diff,
 'save_sha256_before_update':before,
 'save_sha256_after_update_before_launch':after,
 'raw_save_byte_identical_across_update':before==after,
 'stock_loadcareer_slot0_observed':True,
 'career_hub_reached_after_update':True,
 'verdict':'STAGE5_NAME_ONLY_OLD_SAVE_COMPAT_PASS',
}
Path(out).write_text(json.dumps(rec,indent=2,sort_keys=True),encoding='utf-8')
print(json.dumps(rec,indent=2,sort_keys=True))
PY

echo 'STAGE5_NAME_ONLY_OLD_SAVE_COMPAT_PASS'
echo "ARTIFACT_DIR=$OUT"
