#!/usr/bin/env bash
set -euo pipefail

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
EXPECTED_XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
EXPECTED_BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
BT_VERSION='37.0.0'
WORK="${RUNNER_TEMP:-/tmp}/stage0-fingerprint"
OUT="$WORK/out"
rm -rf "$WORK"
mkdir -p "$WORK/xapk" "$OUT"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
[ -n "$SDK_ROOT" ] || { echo 'Android SDK root missing'; exit 2; }
yes | "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null 2>&1 || true
"$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --install "build-tools;$BT_VERSION" >/dev/null
AAPT="$SDK_ROOT/build-tools/$BT_VERSION/aapt"
APKSIGNER="$SDK_ROOT/build-tools/$BT_VERSION/apksigner"
[ -x "$AAPT" ] && [ -x "$APKSIGNER" ] || { echo 'Pinned Android build-tools unavailable'; exit 3; }

curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$WORK/NSS-Base.xapk"
echo "$EXPECTED_XAPK_SHA  $WORK/NSS-Base.xapk" | sha256sum -c -
unzip -tq "$WORK/NSS-Base.xapk" >/dev/null
unzip -q "$WORK/NSS-Base.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$EXPECTED_BASE_SHA  $BASE" | sha256sum -c -

"$AAPT" dump badging "$BASE" > "$OUT/aapt-badging.txt"
"$APKSIGNER" verify --verbose --print-certs "$BASE" > "$OUT/apksigner-certs.txt"

python3 - "$WORK/NSS-Base.xapk" "$WORK/xapk" "$OUT/aapt-badging.txt" "$OUT/apksigner-certs.txt" "$OUT/NSS431_CANONICAL.json" <<'PY'
from pathlib import Path
import hashlib, json, re, sys, zipfile
xapk_path=Path(sys.argv[1]); xdir=Path(sys.argv[2]); badging=Path(sys.argv[3]).read_text(errors='replace'); certs=Path(sys.argv[4]).read_text(errors='replace'); out=Path(sys.argv[5])

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def size(p): return Path(p).stat().st_size
pkg=re.search(r"package: name='([^']+)' versionCode='([^']+)' versionName='([^']+)'",badging)
if not pkg: raise SystemExit('Could not parse aapt package/version')
cert_sha256=re.search(r"Signer #1 certificate SHA-256 digest: ([0-9a-fA-F]+)",certs)
cert_sha1=re.search(r"Signer #1 certificate SHA-1 digest: ([0-9a-fA-F]+)",certs)
cert_dn=re.search(r"Signer #1 certificate DN: (.+)",certs)
if not (cert_sha256 and cert_sha1): raise SystemExit('Could not parse signer certificate')
with zipfile.ZipFile(xapk_path) as z:
    entries=sorted(i.filename for i in z.infolist() if not i.is_dir())
apks=[]
for name in entries:
    if name.lower().endswith('.apk'):
        p=xdir/name
        if not p.is_file(): raise SystemExit(f'Missing extracted APK: {name}')
        apks.append({'name':name,'size':size(p),'sha256':sha256(p)})
base=next((x for x in apks if x['name']=='com.newstargames.newstarsoccer.apk'),None)
if not base: raise SystemExit('Base APK entry not found')
data={
 'schema':1,
 'identity':'New Star Soccer 4.31 stock canonical baseline',
 'package':pkg.group(1),
 'version_code':int(pkg.group(2)),
 'version_name':pkg.group(3),
 'source':{
   'provider':'APKPure',
   'version_code':137,
   'url_template':'https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
 },
 'xapk':{'name':'NSS-Base.xapk','size':size(xapk_path),'sha256':sha256(xapk_path)},
 'base_apk':{
   **base,
   'signer_certificate_dn': cert_dn.group(1).strip() if cert_dn else None,
   'signer_certificate_sha256':cert_sha256.group(1).lower(),
   'signer_certificate_sha1':cert_sha1.group(1).lower()
 },
 'apk_entries':apks,
 'expected_xapk_entries':entries,
 'toolchain_capture':{'android_build_tools': '37.0.0'}
}
out.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(out.read_text())
PY

cp "$OUT/NSS431_CANONICAL.json" "$GITHUB_WORKSPACE/NSS431_CANONICAL.json"
echo 'STAGE0_FINGERPRINT_CAPTURE_PASS'
