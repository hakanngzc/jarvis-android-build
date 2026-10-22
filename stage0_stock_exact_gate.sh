#!/usr/bin/env bash
set -euo pipefail

PKG='com.newstargames.newstarsoccer'
VERSION_NAME='4.31'
VERSION_CODE='137'
BUILD_TOOLS_VERSION='35.0.0'
URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

OUT="$RUNNER_TEMP/stage0-foundation"
WORK="$RUNNER_TEMP/stage0-stock-work"
rm -rf "$OUT" "$WORK"
mkdir -p "$OUT" "$WORK/xapk"

BT="$ANDROID_HOME/build-tools/$BUILD_TOOLS_VERSION"
AAPT="$BT/aapt"
APKSIGNER="$BT/apksigner"
[ -x "$AAPT" ] || { echo "Pinned aapt missing: $AAPT"; exit 10; }
[ -x "$APKSIGNER" ] || { echo "Pinned apksigner missing: $APKSIGNER"; exit 11; }

curl -fL --retry 3 \
  -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' \
  -e "$REFERER" "$URL" -o "$WORK/NSS-Base.xapk"
echo "$XAPK_SHA  $WORK/NSS-Base.xapk" | sha256sum -c -
unzip -tq "$WORK/NSS-Base.xapk" >/dev/null
unzip -q "$WORK/NSS-Base.xapk" -d "$WORK/xapk"

BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
[ -f "$BASE" ] || { echo 'Canonical base APK entry is missing'; exit 12; }
echo "$BASE_SHA  $BASE" | sha256sum -c -

# Read-only inspection only. Legacy stock metadata/signing can make modern
# tooling return non-zero while still printing the data we need; preserve the
# output and validate its parsed contents explicitly below.
"$AAPT" dump badging "$BASE" > "$OUT/base-badging.txt" 2>&1 || true
"$APKSIGNER" verify --print-certs "$BASE" > "$OUT/base-signer.txt" 2>&1 || true
sha256sum "$WORK/NSS-Base.xapk" "$WORK/xapk"/*.apk > "$OUT/sha256sums.txt"

python3 - "$WORK/NSS-Base.xapk" "$BASE" "$OUT/base-badging.txt" "$OUT/base-signer.txt" "$OUT/NSS431_CANONICAL.json" <<'PY'
import hashlib, json, re, sys, zipfile
from pathlib import Path
xapk_path, base_path, badging_path, signer_path, out_path = map(Path, sys.argv[1:])
def sha256_file(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()
badging=badging_path.read_text(encoding='utf-8',errors='replace')
signer=signer_path.read_text(encoding='utf-8',errors='replace')
m=re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'",badging)
if not m: raise SystemExit('Could not parse package/version from aapt badging')
package,version_code,version_name=m.groups()
cm=re.search(r'certificate SHA-256 digest:\s*([0-9A-Fa-f:]+)',signer)
if not cm: raise SystemExit('Could not parse original signer SHA-256 from apksigner output: '+signer[:500])
cert_sha256=cm.group(1).replace(':','').lower()
dm=re.search(r'certificate DN:\s*(.+)',signer)
cert_dn=dm.group(1).strip() if dm else None
with zipfile.ZipFile(xapk_path) as z:
    files=sorted(i.filename for i in z.infolist() if not i.is_dir())
    apk_names=sorted(n for n in files if n.lower().endswith('.apk'))
    apk_entries=[]
    for name in apk_names:
        p=xapk_path.parent/'xapk'/name
        apk_entries.append({'filename':name,'size':p.stat().st_size,'sha256':sha256_file(p)})
    xapk_manifest=None
    if 'manifest.json' in files:
        try: xapk_manifest=json.loads(z.read('manifest.json').decode('utf-8'))
        except Exception: pass
data={
 'schema':1,
 'identity':'NSS 4.31 canonical stock baseline',
 'package':package,
 'version_name':version_name,
 'version_code':int(version_code),
 'xapk':{'filename':'NSS-Base.xapk','size':xapk_path.stat().st_size,'sha256':sha256_file(xapk_path),'source_url':'https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'},
 'base_apk':{'filename':'com.newstargames.newstarsoccer.apk','size':base_path.stat().st_size,'sha256':sha256_file(base_path),'signer_certificate_sha256':cert_sha256,'signer_certificate_dn':cert_dn},
 'apk_entries':apk_entries,
 'expected_xapk_entries':files,
 'xapk_manifest':xapk_manifest,
}
assert data['package']=='com.newstargames.newstarsoccer'
assert data['version_name']=='4.31'
assert data['version_code']==137
assert data['xapk']['sha256']=='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
assert data['base_apk']['sha256']=='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
assert len(cert_sha256)==64
out_path.write_text(json.dumps(data,indent=2,sort_keys=False)+'\n',encoding='utf-8')
print(json.dumps(data,indent=2))
PY

TR="$WORK/xapk/config.tr.apk"
DENSITY="$WORK/xapk/config.xxhdpi.apk"
[ -f "$TR" ] || { echo 'Expected stock config.tr.apk missing'; exit 13; }
[ -f "$DENSITY" ] || { echo 'Expected stock config.xxhdpi.apk missing'; exit 14; }

echo "$BASE_SHA  $BASE" | sha256sum -c -
adb wait-for-device
adb shell pm uninstall "$PKG" >/dev/null 2>&1 || true
adb shell settings put system system_locales tr-TR >/dev/null 2>&1 || true
adb install-multiple -r "$BASE" "$TR" "$DENSITY" | tee "$OUT/install.txt"
adb shell pm clear "$PKG" >/dev/null || true
adb logcat -c >/dev/null 2>&1 || true
adb shell am start -n "$PKG/.MonkeyGame" | tee "$OUT/start.txt"

RESUMED=0
for i in $(seq 1 45); do
  sleep 2
  adb shell dumpsys activity activities > "$WORK/activity-live.txt" 2>/dev/null || true
  PID="$(adb shell pidof "$PKG" | tr -d '\r' || true)"
  if [ -n "$PID" ] && grep -qE 'ResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|mResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|topResumedActivity=.*com\.newstargames\.newstarsoccer.*MonkeyGame' "$WORK/activity-live.txt"; then
    RESUMED=1; echo "Stock NSS resumed on probe $i; pid=$PID"; break
  fi
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qE 'ANR in com\.newstargames\.newstarsoccer|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    echo 'NSS-owned fatal/ANR observed before stable resume'; break
  fi
done

adb exec-out screencap -p > "$OUT/stock-byte-exact.png" || true
adb logcat -d -v threadtime > "$OUT/logcat.txt" || true
adb shell dumpsys activity activities > "$OUT/activity.txt" || true
adb shell dumpsys window windows > "$OUT/window.txt" || true
adb shell dumpsys package "$PKG" > "$OUT/package.txt" || true
adb shell pidof "$PKG" > "$OUT/pid.txt" 2>/dev/null || true

[ "$RESUMED" -eq 1 ] || { echo 'Byte-exact stock NSS never became the resumed activity'; exit 20; }
[ -s "$OUT/pid.txt" ] || { echo 'Byte-exact stock NSS process is not alive'; exit 21; }
[ "$(wc -c < "$OUT/stock-byte-exact.png")" -gt 10000 ] || { echo 'Stock screenshot is unexpectedly small'; exit 22; }
if grep -qE 'ANR in com\.newstargames\.newstarsoccer|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer' "$OUT/logcat.txt"; then
  echo 'NSS-owned crash/ANR found in final byte-exact stock log'; exit 23
fi
grep -q "versionCode=$VERSION_CODE" "$OUT/package.txt" || { echo 'Installed stock versionCode mismatch'; exit 24; }
grep -q "versionName=$VERSION_NAME" "$OUT/package.txt" || { echo 'Installed stock versionName mismatch'; exit 25; }

cat > "$OUT/STAGE0_STOCK_EXACT.txt" <<EOF
PASS canonical XAPK SHA-256 = $XAPK_SHA
PASS canonical base APK SHA-256 = $BASE_SHA
PASS package = $PKG
PASS versionName = $VERSION_NAME
PASS versionCode = $VERSION_CODE
PASS original signed base + original config.tr + original config.xxhdpi installed without patch/repack/align/resign
PASS MonkeyGame became resumed activity
PASS NSS process remained alive
PASS stock screenshot captured
PASS no NSS-owned crash/ANR in final log
VERDICT=STAGE0_BYTE_EXACT_STOCK_PASS
EOF
cat "$OUT/STAGE0_STOCK_EXACT.txt"
echo 'STAGE0_BYTE_EXACT_STOCK_PASS'
