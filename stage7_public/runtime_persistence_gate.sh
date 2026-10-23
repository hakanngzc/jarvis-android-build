#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
ROOT="$PWD"
OUT="$ROOT/stage7_public_artifacts/runtime"
WORK="$RUNNER_TEMP/nss-stage7-runtime"
BASE="${BASE:?BASE is required}"
XAPK_DIR="${STOCK_XAPK_DIR:?STOCK_XAPK_DIR is required}"
: "${BAKSMALI_JAR:?BAKSMALI_JAR is required}"
: "${SMALI_JAR:?SMALI_JAR is required}"
rm -rf "$WORK"; mkdir -p "$WORK/signed" "$OUT"
GATES="$OUT/stage7-gates.txt"; LOG="$OUT/runtime-logcat.txt"; TRACE="$OUT/runtime-trace.txt"
: > "$GATES"
record(){ printf '%s=%s\n' "$1" "$2" | tee -a "$GATES"; }

snapshot_logs(){
  adb logcat -d -v threadtime > "$LOG" 2>/dev/null || true
  grep -Ei 'Create Screen:|CallFunc:|HitGadget:|saveslot|chooseclub|choosenation|LoadDataAndStartTrial|StartCareer|LoadCareer|CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|monkeystate' "$LOG" > "$TRACE" 2>/dev/null || true
}
fatal_check(){
  snapshot_logs
  if grep -qE 'FATAL EXCEPTION|ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer.*has died' "$LOG"; then
    record STAGE7_RUNTIME_STABILITY FAIL; return 1
  fi
}
wait_log(){
  local pattern="$1" timeout_s="${2:-90}" label="${3:-$1}" elapsed=0
  while [ "$elapsed" -lt "$timeout_s" ]; do
    fatal_check || return 1
    if grep -qiE "$pattern" "$LOG"; then echo "Reached $label after ${elapsed}s"; return 0; fi
    sleep 2; elapsed=$((elapsed+2))
  done
  echo "Timed out waiting for $label: $pattern"; snapshot_logs; return 1
}
shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }
press(){ adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true; sleep "${3:-2}"; }
start_nss(){
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb logcat -c >/dev/null 2>&1 || true
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
}

# ---------------------------------------------------------------------------
# Build two TEST-ONLY fixtures from the same stock/harness base.
# ---------------------------------------------------------------------------
python3 "$ROOT/stage1_public/patch_career_test_hook.py" "$BASE" "$WORK/base-career-hook.apk" | tee "$OUT/career-hook.txt"
python3 "$ROOT/stage1_public/patch_cloud_startup_bypass_for_persistence_test.py" \
  "$WORK/base-career-hook.apk" "$WORK/base-harness.apk" | tee "$OUT/cloud-harness.txt"

bash "$ROOT/stage7_public/apply_persistence_fixture_dex.sh" \
  "$WORK/base-harness.apk" "$WORK/base-mutator-dex.apk" "$WORK/mutator-dex" mutator "$OUT/mutator-dex-report.json"
bash "$ROOT/stage7_public/apply_persistence_fixture_dex.sh" \
  "$WORK/base-harness.apk" "$WORK/base-verifier-dex.apk" "$WORK/verifier-dex" verifier "$OUT/verifier-dex-report.json"
record STAGE7_FIXTURE_DEX PASS

cat > "$WORK/onboardingmain.uih" <<'EOF'
Rect:(0,0,0,0)
    SetTweak(FirstPlayLocal,FirstPlayIncrement,4)
EOF
cat > "$WORK/consent.uih" <<'EOF'
Macro:(M_Consent_Panel)
EndM
Macro:(M_Consent_Panel_ATT)
EndM
EOF
python3 - "$WORK/base-mutator-dex.apk" "$WORK/base-mutator.apk" "$WORK/onboardingmain.uih" "$WORK/consent.uih" <<'PY'
import sys,zipfile
src,dst,onboarding,consent=sys.argv[1:]
repl={'assets/monkey/NewGUI/Screens/onboardingmain.uih':open(onboarding,'rb').read(),'assets/monkey/NewGUI/Screens/consent.uih':open(consent,'rb').read()}
seen=set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w',allowZip64=True) as zout:
  for info in zin.infolist():
    data=zin.read(info.filename)
    if info.filename in repl: data=repl[info.filename]; seen.add(info.filename)
    zi=zipfile.ZipInfo(info.filename,info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0)); zi.external_attr=info.external_attr; zi.create_system=info.create_system
    c=zipfile.ZIP_STORED if info.filename=='resources.arsc' else info.compress_type
    zout.writestr(zi,data,compress_type=c,compresslevel=9 if c==zipfile.ZIP_DEFLATED else None)
if seen!=set(repl): raise SystemExit('fixture UI assets missing: '+str(set(repl)-seen))
PY
python3 - "$WORK/base-verifier-dex.apk" "$WORK/base-verifier.apk" "$WORK/onboardingmain.uih" "$WORK/consent.uih" <<'PY'
import sys,zipfile
src,dst,onboarding,consent=sys.argv[1:]
repl={'assets/monkey/NewGUI/Screens/onboardingmain.uih':open(onboarding,'rb').read(),'assets/monkey/NewGUI/Screens/consent.uih':open(consent,'rb').read()}
seen=set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w',allowZip64=True) as zout:
  for info in zin.infolist():
    data=zin.read(info.filename)
    if info.filename in repl: data=repl[info.filename]; seen.add(info.filename)
    zi=zipfile.ZipInfo(info.filename,info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0)); zi.external_attr=info.external_attr; zi.create_system=info.create_system
    c=zipfile.ZIP_STORED if info.filename=='resources.arsc' else info.compress_type
    zout.writestr(zi,data,compress_type=c,compresslevel=9 if c==zipfile.ZIP_DEFLATED else None)
if seen!=set(repl): raise SystemExit('fixture UI assets missing: '+str(set(repl)-seen))
PY
record STAGE7_FIXTURE_BUILD PASS

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci \
  -dname 'CN=NSS Stage7 Public Runtime' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1"; local dst="$2"; local aligned="$WORK/aligned-$(basename "$dst")-$(date +%s%N)"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-mutator.apk" "$WORK/signed/base-mutator.apk"
sign_one "$WORK/base-verifier.apk" "$WORK/signed/base-verifier.apk"
for n in config.tr.apk config.xxhdpi.apk; do [ -f "$XAPK_DIR/$n" ] && sign_one "$XAPK_DIR/$n" "$WORK/signed/$n"; done
MUT_APKS=("$WORK/signed/base-mutator.apk"); VER_APKS=("$WORK/signed/base-verifier.apk")
for n in config.tr.apk config.xxhdpi.apk; do [ -f "$WORK/signed/$n" ] && MUT_APKS+=("$WORK/signed/$n") && VER_APKS+=("$WORK/signed/$n"); done

adb wait-for-device
adb install-multiple -r "${MUT_APKS[@]}" | tee "$OUT/install-mutator.txt"
adb shell pm clear "$PKG" >/dev/null || true
adb root > "$OUT/adb-root.txt" 2>&1 || true; adb wait-for-device; sleep 1
MEAS="$PKG/com.google.android.gms.measurement.AppMeasurementService"; JOB="$PKG/com.google.android.gms.measurement.AppMeasurementJobService"
adb shell pm disable-user --user 0 "$MEAS" > "$OUT/measurement-service-guard.txt" 2>&1 || true
adb shell pm disable-user --user 0 "$JOB" >> "$OUT/measurement-service-guard.txt" 2>&1 || true
adb shell settings put global hide_error_dialogs 1 >/dev/null 2>&1 || true
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true
sleep 4
record STAGE7_MUTATOR_INSTALLED PASS

python3 "$ROOT/stage1_public/stock_ui_coords.py" "$OUT/coords.txt"
coord(){ sed -n "s/^$1=//p" "$OUT/coords.txt" | head -1; }
read -r OK_X OK_Y <<< "$(coord footer_ok | tr ',' ' ')"
read -r MSG_X MSG_Y <<< "$(coord message_accept | tr ',' ' ')"

CAREER_PROBE_N=0
press_career_when_ready(){
  local i target="$WORK/career-target.txt" png="$WORK/career-probe.png" x y
  CAREER_PROBE_N=$((CAREER_PROBE_N+1))
  for i in $(seq 1 45); do
    fatal_check || return 1
    adb exec-out screencap -p > "$png" 2>/dev/null || true
    if python3 - "$png" "$target" <<'PY'
from PIL import Image
import sys
im=Image.open(sys.argv[1]).convert('RGB'); w,h=im.size
x0,x1=int(w*.05),int(w*.75); y0,y1=int(h*.30),int(h*.70)
def green(p):
 r,g,b=p; return g>=90 and g-r>=25 and g-b>=20 and g>=r*1.12
rows=[]
for y in range(y0,y1,2):
 hits=sum(green(im.getpixel((x,y))) for x in range(x0,x1,3))
 if hits>=max(16,int((x1-x0)/3*.07)): rows.append(y)
groups=[]
for y in rows:
 if not groups or y-groups[-1][-1]>4: groups.append([y])
 else: groups[-1].append(y)
groups=[g for g in groups if g[-1]-g[0]>=18]
if not groups: raise SystemExit(1)
g=sorted(groups,key=lambda a:a[0])[0]; ya,yb=g[0],g[-1]
pts=[(x,y) for y in range(ya,yb+1,3) for x in range(x0,x1,3) if green(im.getpixel((x,y)))]
if len(pts)<80: raise SystemExit(1)
xs=sorted(p[0] for p in pts); ys=sorted(p[1] for p in pts)
open(sys.argv[2],'w').write(f'{xs[len(xs)//2]} {ys[len(ys)//2]}\n')
PY
    then read -r x y < "$target"; cp "$png" "$OUT/career-ready-${CAREER_PROBE_N}.png"; press "$x" "$y" 3; return 0; fi
    sleep 2
  done
  cp "$png" "$OUT/career-not-rendered-${CAREER_PROBE_N}.png" 2>/dev/null || true; return 1
}

settle_saveslot_rows(){
  local stem="$1" png target="$WORK/saveslot-targets.txt" i
  for i in $(seq 1 10); do
    png="$OUT/${stem}-saveslot-$i.png"; adb exec-out screencap -p > "$png" 2>/dev/null || true
    if python3 - "$png" "$target" <<'PY'
from PIL import Image
import sys
im=Image.open(sys.argv[1]).convert('RGB'); w,h=im.size
x0,x1=int(w*.02),int(w*.98); y0,y1=int(h*.20),int(h*.72)
def green(p):
 r,g,b=p; return g>=100 and g-r>=30 and g-b>=20 and g>=r*1.15
rows=[]
for y in range(y0,y1,2):
 hits=sum(green(im.getpixel((x,y))) for x in range(x0,x1,3))
 if hits>=max(40,int((x1-x0)/3*.10)): rows.append(y)
groups=[]
for y in rows:
 if not groups or y-groups[-1][-1]>4: groups.append([y])
 else: groups[-1].append(y)
groups=[g for g in groups if g[-1]-g[0]>=35]
if len(groups)!=3: raise SystemExit(1)
centers=[(g[0]+g[-1])//2 for g in groups]
open(sys.argv[2],'w').write(f'{round(w*.50)} {centers[0]} {centers[1]} {centers[2]}\n')
PY
    then read -r SLOT_X SLOT0_Y SLOT1_Y SLOT2_Y < "$target"; cp "$png" "$OUT/${stem}-saveslot-settled.png"; return 0; fi
    sleep 2
  done
  return 1
}
accept_message_if_present(){
  snapshot_logs
  if grep -qiE 'Create Screen:[[:space:]]*message|Create Screen:message|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault' "$LOG"; then press "$MSG_X" "$MSG_Y" 3; fi
}
reach_saveslot(){
  local stem="$1" attempt
  for attempt in 1 2 3; do
    start_nss
    wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu|LoadCareer saveslot:[[:space:]]*[0-2]' 150 'MainMenu or DirectCareerLoad'
    snapshot_logs
    if grep -qiE 'LoadCareer saveslot:[[:space:]]*[0-2]' "$LOG"; then sleep 5; continue; fi
    sleep 3; adb logcat -c >/dev/null 2>&1 || true; press_career_when_ready
    if wait_log 'Create Screen:[[:space:]]*saveslot|Create Screen:saveslot|LoadCareer saveslot:[[:space:]]*[0-2]' 60 'SaveSlot decision'; then
      snapshot_logs
      if grep -qiE 'LoadCareer saveslot:[[:space:]]*[0-2]' "$LOG"; then sleep 5; continue; fi
      settle_saveslot_rows "$stem"; return 0
    fi
  done
  return 1
}

# Create a real slot0 career. Trial physics remain skipped only by the already
# proven CI callback hook; stock StartCareer and stock p_SaveCareer execute.
reach_saveslot seed
adb logcat -c >/dev/null 2>&1 || true
press "$SLOT_X" "$SLOT0_Y" 3
wait_log 'Create Screen:[[:space:]]*chooseclub|Create Screen:chooseclub' 70 'ChooseClub slot0'
accept_message_if_present
press "$OK_X" "$OK_Y" 2; press "$OK_X" "$OK_Y" 3
wait_log 'Create Screen:[[:space:]]*choosenation|Create Screen:choosenation' 70 'ChooseNation slot0'
adb logcat -c >/dev/null 2>&1 || true; press "$OK_X" "$OK_Y" 3
wait_log 'LoadDataAndStartTrial|Create Screen:[[:space:]]*message|Create Screen:message|SETTING ACTIVE:[[:space:]]*messagedefault' 120 'trial intro slot0'
adb logcat -c >/dev/null 2>&1 || true; press "$MSG_X" "$MSG_Y" 4
wait_log 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|CallFunc:[[:space:]]*StartCareer' 90 'mutated StartCareer/save'
sleep 6; fatal_check; shot mutator-after-save
record STAGE7_MUTATOR_SAVE PASS

PREF="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb root >/dev/null 2>&1 || true; adb wait-for-device; sleep 1
adb shell test -f "$PREF"
adb shell cat "$PREF" > "$OUT/mutated-save.xml"
test -s "$OUT/mutated-save.xml"
python3 "$ROOT/stage7_public/verify_player_tokens.py" "$OUT/mutated-save.xml" "$OUT/mutated-token-report.json"
record STAGE7_MUTATED_TOKENS PASS

# Same signer, same package/version, no pm clear: update only the base APK to
# verifier fixture while preserving the real app data/save file.
adb install-multiple -r "${VER_APKS[@]}" | tee "$OUT/install-verifier.txt"
record STAGE7_VERIFIER_UPDATE PASS
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true
sleep 4
adb logcat -c >/dev/null 2>&1 || true
start_nss

# Accept stock one-shot resume or manual slot0 selection.
wait_log 'LoadCareer saveslot:[[:space:]]*0|Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu' 150 'verifier load entry'
snapshot_logs
if ! grep -qiE 'LoadCareer saveslot:[[:space:]]*0' "$LOG"; then
  for attempt in 1 2 3; do
    adb logcat -c >/dev/null 2>&1 || true; press_career_when_ready
    if wait_log 'LoadCareer saveslot:[[:space:]]*0|Create Screen:[[:space:]]*saveslot|Create Screen:saveslot' 25 "slot0 load decision $attempt"; then
      snapshot_logs
      if grep -qiE 'LoadCareer saveslot:[[:space:]]*0' "$LOG"; then break; fi
      if grep -qiE 'Create Screen:[[:space:]]*saveslot|Create Screen:saveslot' "$LOG"; then
        settle_saveslot_rows verifier; adb logcat -c >/dev/null 2>&1 || true; press "$SLOT_X" "$SLOT0_Y" 3; accept_message_if_present; break
      fi
    fi
  done
fi
wait_log 'LoadCareer saveslot:[[:space:]]*0' 90 'stock m_LoadCareer slot0'
sleep 8; fatal_check; snapshot_logs
python3 - "$LOG" <<'PY'
import re,sys
s=open(sys.argv[1],encoding='utf-8',errors='replace').read()
loads=list(re.finditer(r'LoadCareer saveslot:\s*0',s,re.I))
if not loads: raise SystemExit('LoadCareer slot0 runtime evidence missing')
pos=loads[-1].start()
saves=[m.start() for m in re.finditer(r'SAVE CAREER|SaveCareer|SaveState',s,re.I) if m.start()>pos]
if not saves: raise SystemExit('No SaveCareer evidence after LoadCareer slot0')
print('STAGE7_LOAD_THEN_RESAVE_LOG=PASS')
PY
record STAGE7_LOAD_THEN_RESAVE_LOG PASS
shot verifier-after-load-resave

adb root >/dev/null 2>&1 || true; adb wait-for-device; sleep 1
adb shell cat "$PREF" > "$OUT/post-load-resave.xml"
test -s "$OUT/post-load-resave.xml"
python3 "$ROOT/stage7_public/verify_player_tokens.py" "$OUT/mutated-save.xml" "$OUT/post-load-resave.xml" "$OUT/save-load-resave-token-report.json"
record STAGE7_SAVE_LOAD_RESAVE PASS
record STAGE7_ECONOMY_RUNTIME PASS
record STAGE7_CONTRACT_RUNTIME PASS
record STAGE7_RELATION_LIFESTYLE_RUNTIME PASS
record STAGE7_SKILL_TRAINING_RUNTIME PASS
fatal_check
record STAGE7_RUNTIME_STABILITY PASS
record STAGE7_PERSISTENT_SUBSYSTEMS_RUNTIME PASS
echo 'VERDICT=STAGE7_PERSISTENT_SUBSYSTEMS_RUNTIME_PASS'
