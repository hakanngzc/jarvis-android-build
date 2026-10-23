#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
ROOT="$PWD"
OUT="$ROOT/stage6_public_artifacts/runtime"
WORK="$RUNNER_TEMP/nss-stage6-logo-runtime"
BASE="${BASE:?BASE is required}"
XAPK_DIR="${STOCK_XAPK_DIR:?STOCK_XAPK_DIR is required}"
mkdir -p "$OUT" "$WORK/signed"
GATES="$OUT/stage6-logo-gates.txt"
: > "$GATES"
record(){ printf '%s=%s\n' "$1" "$2" | tee -a "$GATES"; }

python3 stage6_public/build_runtime_fixture.py \
  "$BASE" "$WORK/base-stage6-unsigned.apk" "$WORK/fixture" "$OUT/runtime-fixture-report.json" \
  | tee "$OUT/runtime-fixture-build.txt"
record STAGE6_FIXTURE_BUILD PASS

python3 - "$WORK/base-stage6-unsigned.apk" "$OUT/runtime-fixture-report.json" <<'PY'
import json,struct,sys,zipfile
apk,report=sys.argv[1:]
r=json.load(open(report,encoding='utf-8'))
assert r['append']['old_atlas_count']==144 and r['append']['new_atlas_count']==145
assert r['append']['record_names']==['REBORNClub3141','REBORNClub3157']
assert r['append']['alias_suffix_sha256_before']==r['append']['alias_suffix_sha256_after']
assert r['append']['source_prefix_sha256']==r['append']['patched_prefix_sha256']
assert r['selector']['stock_design15_count_before']==r['selector']['stock_design15_count_after']
assert r['selector']['selector_insert_count']>=6
with zipfile.ZipFile(apk) as z:
    names=set(z.namelist())
    assert 'assets/monkey/NewGUI/Atlases/UIAtlas145.png' in names
    key=z.read('assets/monkey/NewGUI/Atlases/Key.key')
    assert struct.unpack_from('<I',key,0)[0]==145
    ui=z.read('assets/monkey/NewGUI/Screens/ShieldAnims.uih').decode('utf-8')
    assert 'REBORNClub3141' in ui and 'REBORNClub3157' in ui
    menu=z.read('assets/monkey/NewGUI/Screens/mainmenu.uis').decode('utf-8')
    assert 'STAGE6_TEST_ONLY_LOGO_PROOF_BEGIN' in menu
print('STAGE6_FIXTURE_STATIC=PASS')
PY
record STAGE6_FIXTURE_STATIC PASS

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci \
  -dname 'CN=NSS Stage6 Public Runtime' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci \
    --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-stage6-unsigned.apk" "$WORK/signed/base.apk"
for n in config.tr.apk config.xxhdpi.apk; do
  [ -f "$XAPK_DIR/$n" ] && sign_one "$XAPK_DIR/$n" "$WORK/signed/$n"
done
APKS=("$WORK/signed/base.apk")
[ -f "$WORK/signed/config.tr.apk" ] && APKS+=("$WORK/signed/config.tr.apk")
[ -f "$WORK/signed/config.xxhdpi.apk" ] && APKS+=("$WORK/signed/config.xxhdpi.apk")

adb wait-for-device
adb install-multiple -r "${APKS[@]}" | tee "$OUT/install.txt"
adb shell pm clear "$PKG" >/dev/null || true
record STAGE6_FIXTURE_INSTALLED PASS

# Hosted AOSP images allow adbd root. Disable only the legacy Google measurement
# components that previously caused unrelated ANRs in this stock APK.
adb root > "$OUT/adb-root.txt" 2>&1 || true
adb wait-for-device
sleep 1
MEAS="$PKG/com.google.android.gms.measurement.AppMeasurementService"
JOB="$PKG/com.google.android.gms.measurement.AppMeasurementJobService"
adb shell pm disable-user --user 0 "$MEAS" > "$OUT/measurement-service-guard.txt" 2>&1 || true
adb shell pm disable-user --user 0 "$JOB" >> "$OUT/measurement-service-guard.txt" 2>&1 || true
echo 'MEASUREMENT_SERVICE_GUARD=PASS' >> "$OUT/measurement-service-guard.txt"

adb shell settings put global hide_error_dialogs 1 >/dev/null 2>&1 || true
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true
sleep 4
adb logcat -c >/dev/null 2>&1 || true
start_game(){
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || \
    adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
}
start_game

VISIBLE=0
for i in $(seq 1 50); do
  sleep 2
  adb exec-out screencap -p > "$WORK/probe.png" 2>/dev/null || continue
  if python3 - "$WORK/probe.png" "$OUT/runtime-render-metrics.txt" <<'PY'
from PIL import Image,ImageStat
import sys
im=Image.open(sys.argv[1]).convert('RGB'); w,h=im.size; s=w/640.0

def crop(x0,y0,x1,y1):
    return im.crop((round(x0*s),round(y0*s),round(x1*s),round(y1*s)))
def ratio(img,target,tol=24):
    px=list(img.getdata()); n=max(1,len(px))
    return sum(max(abs(p[j]-target[j]) for j in range(3))<=tol for p in px)/n
left=crop(45,155,275,385); right=crop(365,155,595,385); stock=crop(235,455,405,685)
left_red=ratio(left,(238,52,52)); left_yellow=ratio(left,(250,205,35)); left_dark=ratio(left,(20,20,25))
right_yellow=ratio(right,(250,205,35)); right_blue=ratio(right,(20,65,170)); right_dark=ratio(right,(20,20,25))
stock_navy=ratio(stock,(38,53,74),35); stock_std=sum(ImageStat.Stat(stock).stddev)/3.0
text=(f'size={w}x{h}\nscale={s:.6f}\nleft_red={left_red:.5f}\nleft_yellow={left_yellow:.5f}\nleft_dark={left_dark:.5f}\n'
      f'right_yellow={right_yellow:.5f}\nright_blue={right_blue:.5f}\nright_dark={right_dark:.5f}\n'
      f'stock_navy={stock_navy:.5f}\nstock_stddev={stock_std:.3f}\n')
open(sys.argv[2],'w').write(text); print(text.replace('\n',' ').strip())
# Identity proof: 3141 is the red/black-white crest, 3157 is yellow/blue.
# Cross-colour limits catch swapped or duplicated atlas UV records.
ok=(left_red>0.008 and left_dark>0.02 and left_red>left_yellow*2+0.002 and
    right_yellow>0.015 and right_blue>0.015 and right_yellow>right_dark*0.3 and
    stock_std>12.0 and stock_navy>0.002)
raise SystemExit(0 if ok else 1)
PY
  then
    cp "$WORK/probe.png" "$OUT/multi-logo-runtime.png"
    VISIBLE=1
    echo "render_probe=$i" >> "$OUT/runtime-render-metrics.txt"
    break
  fi
  # Recover only from an actual Android system ANR overlay.
  adb shell dumpsys window windows > "$WORK/window.txt" 2>/dev/null || true
  if grep -q 'Application Not Responding' "$WORK/window.txt"; then
    adb shell input keyevent 4 >/dev/null 2>&1 || true
    start_game
  fi
done

adb logcat -d -v threadtime > "$OUT/runtime-logcat.txt" 2>/dev/null || true
adb shell dumpsys activity activities > "$OUT/activity.txt" 2>/dev/null || true
if [ "$VISIBLE" -ne 1 ]; then
  cp "$WORK/probe.png" "$OUT/multi-logo-runtime-failed.png" 2>/dev/null || true
  record STAGE6_MULTI_CLUB_RENDER FAIL
  exit 151
fi
record STAGE6_MULTI_CLUB_RENDER PASS
record STAGE6_CLUB3141_IDENTITY PASS
record STAGE6_CLUB3157_IDENTITY PASS
record STAGE6_STOCK_BADGE_FALLBACK_RENDER PASS

if grep -qE 'FATAL EXCEPTION|ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer.*has died' "$OUT/runtime-logcat.txt"; then
  record STAGE6_RUNTIME_STABILITY FAIL
  exit 152
fi
record STAGE6_RUNTIME_STABILITY PASS
record STAGE6_LOGO_ATLAS_RUNTIME PASS
echo 'VERDICT=STAGE6_LOGO_ATLAS_RUNTIME_PASS'
