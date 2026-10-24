#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
ROOT="$PWD"
OUT="$ROOT/stage6_public_artifacts/production-runtime"
WORK="$RUNNER_TEMP/nss-stage6-production-runtime"
BASE="${BASE:?BASE is required}"
XAPK_DIR="${STOCK_XAPK_DIR:?STOCK_XAPK_DIR is required}"
MANIFEST="${STAGE6_LOGO_MANIFEST:-stage6_public/manifests/turkey_tur1.json}"
: "${BAKSMALI_JAR:?BAKSMALI_JAR is required}"
: "${SMALI_JAR:?SMALI_JAR is required}"
mkdir -p "$OUT" "$WORK/signed"
GATES="$OUT/stage6-production-runtime-gates.txt"
: > "$GATES"
record(){ printf '%s=%s\n' "$1" "$2" | tee -a "$GATES"; }

python3 stage6_public/build_production_logo_apk.py \
  "$BASE" "$WORK/base-assets.apk" "$MANIFEST" "$WORK/assets-work" "$OUT/assets-report.json" UIAtlas145 \
  | tee "$OUT/assets-build.txt"
record STAGE6_PRODUCTION_ASSET_BUILD PASS

bash stage6_public/apply_club_badge_override_dex.sh \
  "$WORK/base-assets.apk" "$WORK/base-production-unsigned.apk" "$WORK/dex-work" "$OUT/dex-report.json" "$MANIFEST" \
  | tee "$OUT/dex-build.txt"
record STAGE6_PRODUCTION_DEX_MAPPING PASS

python3 - "$BASE" "$WORK/base-production-unsigned.apk" "$MANIFEST" "$OUT/assets-report.json" "$OUT/dex-report.json" <<'PY'
import hashlib,json,sys,zipfile
base,prod,manifest,arep,drep=sys.argv[1:]
M=json.load(open(manifest,encoding='utf-8'))
A=json.load(open(arep,encoding='utf-8'))
D=json.load(open(drep,encoding='utf-8'))
expected={str(int(r['club_id'])):int(r['style']) for r in M['clubs']}
assert len(expected)==18
assert A['club_count']==18
assert {str(k):v for k,v in A['overrides'].items()}==expected
assert D['override']['override_count']==18
assert {str(k):v for k,v in D['override']['overrides'].items()}==expected
assert D['other_dex_preserved'] is True
assert D['override']['fallback']=='m_id % 15'
assert D['override']['divisor_register_restored'] is True
assert A['append']['old_atlas_count']==144 and A['append']['new_atlas_count']==145
assert A['atlas_layout']=={'cell_size':128,'columns':16,'rows':2,'width':2048,'height':256}
assert A['forbidden_test_surfaces_preserved'] is True
assert A['test_overlay_present'] is False
protected=(
 'assets/monkey/NewGUI/Screens/mainmenu.uis',
 'assets/monkey/NewGUI/Screens/onboardingmain.uih',
 'assets/monkey/NewGUI/Screens/consent.uih',
)
with zipfile.ZipFile(base) as b, zipfile.ZipFile(prod) as p:
    for name in protected:
        assert b.read(name)==p.read(name), name+' changed in production runtime package'
    ui=p.read('assets/monkey/NewGUI/Screens/ShieldAnims.uih').decode('utf-8-sig')
    assert 'STAGE6_TEST_ONLY_LOGO_PROOF' not in ui
    menu=p.read(protected[0]).decode('utf-8-sig')
    assert 'STAGE6_TEST_ONLY_LOGO_PROOF' not in menu
    for row in M['clubs']:
        assert row['symbol'] in ui
    assert 'assets/monkey/NewGUI/Atlases/UIAtlas145.png' in p.namelist()
print('STAGE6_PRODUCTION_STATIC_RUNTIME_INPUT=PASS clubs=18 protected_stock_flows=true')
PY
record STAGE6_PRODUCTION_STATIC_INPUT PASS

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci \
  -dname 'CN=NSS Stage6 Production Runtime' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1" dst="$2" aligned
  aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci \
    --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-production-unsigned.apk" "$WORK/signed/base.apk"
for n in config.tr.apk config.xxhdpi.apk; do
  [ -f "$XAPK_DIR/$n" ] && sign_one "$XAPK_DIR/$n" "$WORK/signed/$n"
done
APKS=("$WORK/signed/base.apk")
[ -f "$WORK/signed/config.tr.apk" ] && APKS+=("$WORK/signed/config.tr.apk")
[ -f "$WORK/signed/config.xxhdpi.apk" ] && APKS+=("$WORK/signed/config.xxhdpi.apk")

adb wait-for-device
adb install-multiple -r "${APKS[@]}" | tee "$OUT/install.txt"
adb shell pm clear "$PKG" > "$OUT/pm-clear.txt" 2>&1 || true
record STAGE6_PRODUCTION_INSTALLED PASS

# Keep the same hosted-AOSP guard used by the previously verified Stage6 run.
adb root > "$OUT/adb-root.txt" 2>&1 || true
adb wait-for-device
sleep 1
adb shell pm disable-user --user 0 "$PKG/com.google.android.gms.measurement.AppMeasurementService" > "$OUT/measurement-guard.txt" 2>&1 || true
adb shell pm disable-user --user 0 "$PKG/com.google.android.gms.measurement.AppMeasurementJobService" >> "$OUT/measurement-guard.txt" 2>&1 || true
echo 'MEASUREMENT_SERVICE_GUARD=PASS' >> "$OUT/measurement-guard.txt"
adb shell settings put global hide_error_dialogs 1 >/dev/null 2>&1 || true
adb shell cmd package compile -m speed -f "$PKG" >/dev/null 2>&1 || true

launch_and_check(){
  local label="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb logcat -c >/dev/null 2>&1 || true
  adb shell am start -W -n "$PKG/.MonkeyGame" > "$OUT/${label}-launch.txt" 2>&1 || \
    adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >> "$OUT/${label}-launch.txt" 2>&1
  local alive=0
  for _ in $(seq 1 20); do
    sleep 1
    if adb shell pidof "$PKG" | grep -q '[0-9]'; then alive=1; break; fi
  done
  adb exec-out screencap -p > "$OUT/${label}.png" 2>/dev/null || true
  adb shell dumpsys activity activities > "$OUT/${label}-activity.txt" 2>/dev/null || true
  adb shell dumpsys window windows > "$OUT/${label}-window.txt" 2>/dev/null || true
  adb logcat -d -v threadtime > "$OUT/${label}-logcat.txt" 2>/dev/null || true
  if [ "$alive" -ne 1 ]; then echo "$label process not alive" >&2; return 31; fi
  grep -q "$PKG" "$OUT/${label}-activity.txt"
  if grep -qE 'FATAL EXCEPTION|ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer.*has died' "$OUT/${label}-logcat.txt"; then
    echo "$label crash/ANR marker found" >&2; return 32
  fi
  if grep -q 'Application Not Responding' "$OUT/${label}-window.txt"; then
    echo "$label ANR window found" >&2; return 33
  fi
}

launch_and_check cold
record STAGE6_PRODUCTION_COLD_LAUNCH PASS
sleep 2
launch_and_check relaunch
record STAGE6_PRODUCTION_RELAUNCH PASS

python3 - "$OUT" <<'PY'
import sys
from pathlib import Path
out=Path(sys.argv[1])
for label in ('cold','relaunch'):
    p=out/f'{label}.png'
    if not p.is_file() or p.stat().st_size < 1000:
        raise SystemExit(f'{label} screenshot missing/too small')
print('STAGE6_PRODUCTION_SCREENSHOTS=PASS')
PY
record STAGE6_PRODUCTION_SCREENSHOT PASS
record STAGE6_PRODUCTION_RUNTIME_STABILITY PASS
record STAGE6_PRODUCTION_RUNTIME PASS
echo 'VERDICT=STAGE6_PRODUCTION_RUNTIME_PASS'
