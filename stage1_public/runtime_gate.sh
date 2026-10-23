#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
ROOT="$PWD"
OUT="$ROOT/stage1_public_artifacts/runtime"
WORK="$RUNNER_TEMP/nss-stage1-residual"
XAPK_DIR="${STOCK_XAPK_DIR:?STOCK_XAPK_DIR is required}"
BASE="${BASE:?BASE is required}"
mkdir -p "$OUT" "$WORK" "$WORK/signed"
SUMMARY="$OUT/residual-gates.txt"
LOG="$OUT/runtime-logcat.txt"
TRACE="$OUT/runtime-trace.txt"
: > "$SUMMARY"

record(){ printf '%s=%s\n' "$1" "$2" | tee -a "$SUMMARY"; }

snapshot_logs(){
  adb logcat -d -v threadtime > "$LOG" 2>/dev/null || true
  grep -Ei 'Create Screen:|CallFunc:|HitGadget:|saveslot|chooseclub|choosenation|LoadDataAndStartTrial|TrialDone|StartCareer|LoadCareer|DeleteCareer|CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|monkeystate' "$LOG" > "$TRACE" 2>/dev/null || true
}

fatal_check(){
  snapshot_logs
  if grep -qE 'FATAL EXCEPTION|ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer.*has died' "$LOG"; then
    record fatal_runtime FAIL
    return 1
  fi
}

wait_log(){
  local pattern="$1" timeout_s="${2:-90}" label="${3:-$1}" elapsed=0
  while [ "$elapsed" -lt "$timeout_s" ]; do
    fatal_check || return 1
    if grep -qiE "$pattern" "$LOG"; then
      echo "Reached $label after ${elapsed}s"
      return 0
    fi
    sleep 2
    elapsed=$((elapsed+2))
  done
  echo "Timed out waiting for $label: $pattern"
  snapshot_logs
  return 1
}

shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }
press(){
  adb shell input touchscreen swipe "$1" "$2" "$1" "$2" 220 </dev/null || true
  sleep "${3:-2}"
}
start_nss(){
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb logcat -c >/dev/null 2>&1 || true
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || \
    adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
}

# ---------------------------------------------------------------------------
# 1. Build a deterministic TEST-ONLY stock runtime fixture.
#    Persistence implementations themselves remain stock.
# ---------------------------------------------------------------------------
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

python3 "$ROOT/stage1_public/patch_career_test_hook.py" "$BASE" "$WORK/base-hook.apk" | tee "$OUT/career-hook.txt"

python3 - "$WORK/base-hook.apk" "$WORK/base-test-unsigned.apk" "$WORK/onboardingmain.uih" "$WORK/consent.uih" <<'PY'
import sys,zipfile
src,dst,onboarding,consent=sys.argv[1:]
repl={
 'assets/monkey/NewGUI/Screens/onboardingmain.uih':open(onboarding,'rb').read(),
 'assets/monkey/NewGUI/Screens/consent.uih':open(consent,'rb').read(),
}
seen=set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w',allowZip64=True) as zout:
    for info in zin.infolist():
        data=zin.read(info.filename)
        if info.filename in repl:
            data=repl[info.filename]; seen.add(info.filename)
        zi=zipfile.ZipInfo(info.filename, info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0))
        zi.external_attr=info.external_attr; zi.create_system=info.create_system
        zout.writestr(zi,data,compress_type=info.compress_type,
                      compresslevel=9 if info.compress_type==zipfile.ZIP_DEFLATED else None)
if seen != set(repl): raise SystemExit(f'missing fixture assets: {set(repl)-seen}')
print('TEST_ONLY_FTUE_FIXTURE=PASS')
PY

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci \
  -dname 'CN=NSS Stage1 Public Runtime' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1

sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci \
    --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}

sign_one "$WORK/base-test-unsigned.apk" "$WORK/signed/base.apk"
for n in config.tr.apk config.xxhdpi.apk; do
  [ -f "$XAPK_DIR/$n" ] && sign_one "$XAPK_DIR/$n" "$WORK/signed/$n"
done
APKS=("$WORK/signed/base.apk")
[ -f "$WORK/signed/config.tr.apk" ] && APKS+=("$WORK/signed/config.tr.apk")
[ -f "$WORK/signed/config.xxhdpi.apk" ] && APKS+=("$WORK/signed/config.xxhdpi.apk")
adb install-multiple -r "${APKS[@]}" | tee "$OUT/install.txt"
adb shell pm clear "$PKG" >/dev/null || true
record test_fixture_installed PASS

# ---------------------------------------------------------------------------
# 2. Resolve stock UIS coordinates against the actual emulator resolution.
# ---------------------------------------------------------------------------
python3 - "$OUT/coords.txt" <<'PY'
import re,subprocess,sys
s=subprocess.check_output(['adb','shell','wm','size'],text=True)
m=re.findall(r'(\d+)x(\d+)',s)
if not m: raise SystemExit(s)
w,h=map(int,m[-1]); scale=w/640.0
B=h/scale; n=(B-960.0)*0.7+744.0
logical={
 'career':(471,541),
 'slot0':(326,320),'slot1':(326,494),'slot2':(326,668),
 'delete0':(567,319),'delete1':(567,493),'delete2':(567,667),
 'footer_ok':(553,n+85),'message_accept':(477,n+85),
}
with open(sys.argv[1],'w') as f:
    f.write(f'physical={w}x{h}\nscale={scale:.6f}\nlogical_B={B:.3f}\nlogical_n={n:.3f}\n')
    for k,(x,y) in logical.items(): f.write(f'{k}={round(x*scale)},{round(y*scale)}\n')
print(open(sys.argv[1]).read())
PY
coord(){ sed -n "s/^$1=//p" "$OUT/coords.txt" | head -1; }
read -r CAREER_X CAREER_Y <<< "$(coord career | tr ',' ' ')"
read -r SLOT0_X SLOT0_Y <<< "$(coord slot0 | tr ',' ' ')"
read -r SLOT1_X SLOT1_Y <<< "$(coord slot1 | tr ',' ' ')"
read -r SLOT2_X SLOT2_Y <<< "$(coord slot2 | tr ',' ' ')"
read -r DEL1_X DEL1_Y <<< "$(coord delete1 | tr ',' ' ')"
read -r OK_X OK_Y <<< "$(coord footer_ok | tr ',' ' ')"
read -r MSG_X MSG_Y <<< "$(coord message_accept | tr ',' ' ')"

# ---------------------------------------------------------------------------
# 3. Navigation helpers. DirectCareerLoad is one-shot, so reach_saveslot can
#    consume an unexpected auto-resume and retry once without mutating data.
# ---------------------------------------------------------------------------
wait_main_or_load(){
  wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu|LoadCareer saveslot:[[:space:]]*[0-2]' 150 'MainMenu or DirectCareerLoad'
}

reach_saveslot(){
  local stem="$1" attempt
  for attempt in 1 2 3; do
    start_nss
    wait_main_or_load
    snapshot_logs
    if grep -qiE 'LoadCareer saveslot:[[:space:]]*[0-2]' "$LOG"; then
      record "${stem}_consumed_direct_hint_attempt${attempt}" yes
      sleep 5
      continue
    fi
    sleep 3
    shot "${stem}-main-$attempt"
    adb logcat -c >/dev/null 2>&1 || true
    press "$CAREER_X" "$CAREER_Y" 3
    snapshot_logs
    if grep -qiE 'LoadCareer saveslot:[[:space:]]*[0-2]' "$LOG"; then
      record "${stem}_consumed_direct_hint_after_career_attempt${attempt}" yes
      sleep 5
      continue
    fi
    if wait_log 'Create Screen:[[:space:]]*saveslot|Create Screen:saveslot' 60 'SaveSlot'; then
      sleep 4
      shot "${stem}-saveslot"
      return 0
    fi
  done
  echo 'Could not reach SaveSlot after consuming possible one-shot hints'
  return 1
}

accept_message_if_present(){
  snapshot_logs
  if grep -qiE 'Create Screen:[[:space:]]*message|Create Screen:message|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault' "$LOG"; then
    press "$MSG_X" "$MSG_Y" 3
  fi
}

create_career(){
  local slot="$1" stem="$2" sx sy
  case "$slot" in
    0) sx=$SLOT0_X; sy=$SLOT0_Y;;
    1) sx=$SLOT1_X; sy=$SLOT1_Y;;
    2) sx=$SLOT2_X; sy=$SLOT2_Y;;
    *) return 2;;
  esac
  reach_saveslot "$stem-open"
  adb logcat -c >/dev/null 2>&1 || true
  press "$sx" "$sy" 3
  wait_log 'Create Screen:[[:space:]]*chooseclub|Create Screen:chooseclub' 70 "ChooseClub slot $slot"
  shot "$stem-chooseclub"
  # Stock blank-name behavior: first OK supplies default name, second advances.
  press "$OK_X" "$OK_Y" 2
  press "$OK_X" "$OK_Y" 3
  wait_log 'Create Screen:[[:space:]]*choosenation|Create Screen:choosenation' 70 "ChooseNation slot $slot"
  shot "$stem-choosenation"
  adb logcat -c >/dev/null 2>&1 || true
  press "$OK_X" "$OK_Y" 3
  wait_log 'CallFunc:[[:space:]]*LoadDataAndStartTrial|LoadDataAndStartTrial|CallFunc:[[:space:]]*TrialDone|SetActive:[[:space:]]*message|SETTING ACTIVE:[[:space:]]*messagedefault|Create Screen:[[:space:]]*message|Create Screen:message' 120 "trial intro slot $slot"
  shot "$stem-trial-intro"
  adb logcat -c >/dev/null 2>&1 || true
  press "$MSG_X" "$MSG_Y" 4
  # CI hook redirects only the callback; real StartCareer/p_SaveCareer stay stock.
  wait_log 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|CallFunc:[[:space:]]*StartCareer' 90 "StartCareer/save slot $slot"
  sleep 6
  fatal_check
  shot "$stem-after-save"
  record "slot${slot}_create" PASS
}

manual_load_slot(){
  local slot="$1" stem="$2" sx sy
  case "$slot" in
    0) sx=$SLOT0_X; sy=$SLOT0_Y;;
    1) sx=$SLOT1_X; sy=$SLOT1_Y;;
    2) sx=$SLOT2_X; sy=$SLOT2_Y;;
  esac
  reach_saveslot "$stem-open"
  adb logcat -c >/dev/null 2>&1 || true
  press "$sx" "$sy" 3
  snapshot_logs
  if ! grep -qiE "LoadCareer saveslot:[[:space:]]*$slot" "$LOG"; then
    accept_message_if_present
  fi
  wait_log "LoadCareer saveslot:[[:space:]]*$slot" 90 "LoadCareer slot $slot"
  sleep 5
  fatal_check
  shot "$stem-loaded"
  record "slot${slot}_manual_load" PASS
}

# ---------------------------------------------------------------------------
# 4. Establish three real careers. Slot0 is a neighbor-control for deletion.
# ---------------------------------------------------------------------------
create_career 0 slot0-seed
create_career 1 slot1
manual_load_slot 1 slot1-restart
record SLOT1_RUNTIME PASS

create_career 2 slot2

# ---------------------------------------------------------------------------
# 5. Dedicated DirectCareerLoad proof for the last saved slot (slot2).
#    Stock may execute on cold startup or after Career is selected; accept both.
# ---------------------------------------------------------------------------
start_nss
wait_main_or_load
sleep 5
snapshot_logs
if grep -qiE 'LoadCareer saveslot:[[:space:]]*2' "$LOG"; then
  record directcareerload_path startup
else
  if ! grep -qiE 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu' "$LOG"; then
    wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu' 120 'MainMenu before direct Career action'
  fi
  adb logcat -c >/dev/null 2>&1 || true
  press "$CAREER_X" "$CAREER_Y" 3
  snapshot_logs
  if ! grep -qiE 'LoadCareer saveslot:[[:space:]]*2' "$LOG"; then
    accept_message_if_present
  fi
  wait_log 'LoadCareer saveslot:[[:space:]]*2' 90 'DirectCareerLoad slot2'
  record directcareerload_path career_action
fi
shot directcareerload-slot2-loaded
record directcareerload_first_use PASS

# The hint was reset to -1 by p_DirectCareerLoad. Next Career entry must expose
# SaveSlot rather than automatically load slot2 again.
adb logcat -c >/dev/null 2>&1 || true
start_nss
wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu' 150 'MainMenu after direct hint consumed'
sleep 3
adb logcat -c >/dev/null 2>&1 || true
press "$CAREER_X" "$CAREER_Y" 3
wait_log 'Create Screen:[[:space:]]*saveslot|Create Screen:saveslot|LoadCareer saveslot:[[:space:]]*2' 70 'one-shot decision'
snapshot_logs
if grep -qiE 'LoadCareer saveslot:[[:space:]]*2' "$LOG"; then
  record directcareerload_one_shot FAIL
  exit 124
fi
record directcareerload_one_shot PASS
shot directcareerload-one-shot-saveslot
record DIRECTCAREERLOAD_RUNTIME PASS

# Equivalent slot2 manual reload after the direct-resume proof.
manual_load_slot 2 slot2-restart
record SLOT2_RUNTIME PASS

# ---------------------------------------------------------------------------
# 6. DeleteCareer runtime + raw serializer semantics.
# ---------------------------------------------------------------------------
PREF='/data/data/com.newstargames.newstarsoccer/shared_prefs/MonkeyGame.xml'
RAW_AVAILABLE=0
if adb root >/dev/null 2>&1; then
  adb wait-for-device; sleep 2
  if adb shell test -f "$PREF"; then
    adb shell cat "$PREF" > "$OUT/before-delete.xml" 2>/dev/null || true
    [ -s "$OUT/before-delete.xml" ] && RAW_AVAILABLE=1
  fi
fi
record delete_raw_state_before "$RAW_AVAILABLE"

reach_saveslot delete-open
adb logcat -c >/dev/null 2>&1 || true
press "$DEL1_X" "$DEL1_Y" 3
accept_message_if_present
wait_log 'DeleteCareer|Create Screen:[[:space:]]*saveslot|Create Screen:saveslot' 90 'DeleteCareer slot1 return'
sleep 5
fatal_check
shot delete-after
snapshot_logs
if grep -qiE 'DeleteCareer' "$LOG"; then record deletecareer_exact_log PASS; else record deletecareer_exact_log behavioral_only; fi

if [ "$RAW_AVAILABLE" -eq 1 ]; then
  adb shell cat "$PREF" > "$OUT/after-delete.xml" 2>/dev/null || true
  python3 - "$OUT/before-delete.xml" "$OUT/after-delete.xml" > "$OUT/delete-raw-check.txt" <<'PY'
import sys,xml.etree.ElementTree as ET

def vals(path):
    root=ET.parse(path).getroot()
    node=next((e for e in root.iter('string') if e.attrib.get('name')=='.monkeystate'),None)
    if node is None: raise SystemExit(f'{path}: .monkeystate missing')
    a=(node.text or '').split(';')
    if len(a)<15: raise SystemExit(f'{path}: expected >=15 fields, got {len(a)}')
    return a
b=vals(sys.argv[1]); a=vals(sys.argv[2])
for i in (6,7,8):
    if a[i] != '': raise SystemExit(f'slot1 field {i} not cleared')
if not b[9]: raise SystemExit('slot1 base+4 was empty before delete')
if a[9] != b[9]: raise SystemExit('slot1 base+4 changed; stock should preserve stale block')
for i in (1,11):
    if not a[i]: raise SystemExit(f'neighbor principal block {i} became empty')
print('DELETECAREER_RAW_BLOCKS=PASS')
print('slot1_cleared=6,7,8')
print('slot1_stale_preserved=9')
print('neighbors_preserved=1,11')
PY
  record deletecareer_raw_semantics PASS
else
  record deletecareer_raw_semantics unavailable_behavioral_gate_required
fi

# Immediate occupancy decision: deleted slot1 must start a fresh Career.
adb logcat -c >/dev/null 2>&1 || true
press "$SLOT1_X" "$SLOT1_Y" 3
wait_log 'Create Screen:[[:space:]]*chooseclub|Create Screen:chooseclub' 70 'deleted slot1 -> NewCareer'
record deletecareer_immediate_empty PASS
shot deleted-slot1-chooseclub

# Process restart: it must still be empty.
reach_saveslot delete-restart
adb logcat -c >/dev/null 2>&1 || true
press "$SLOT1_X" "$SLOT1_Y" 3
wait_log 'Create Screen:[[:space:]]*chooseclub|Create Screen:chooseclub' 70 'deleted slot1 remains empty after restart'
record deletecareer_restart_empty PASS

# Neighbor careers must survive deletion.
manual_load_slot 0 delete-neighbor-slot0
record deletecareer_slot0_preserved PASS
manual_load_slot 2 delete-neighbor-slot2
record deletecareer_slot2_preserved PASS
record DELETECAREER_RUNTIME PASS

record RESIDUAL_STAGE1_RUNTIME PASS
echo 'VERDICT=STAGE1_PUBLIC_STOCK_RESIDUAL_RUNTIME_PASS'
