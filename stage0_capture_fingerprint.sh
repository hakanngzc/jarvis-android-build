#!/usr/bin/env bash
set -euo pipefail

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
EXPECTED_XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
EXPECTED_BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
EXPECTED_CERT_SHA1='eb94af17f8335fc62cff5a19517946c3dbdcaea8'
BT_VERSION='37.0.0'
WORK="${RUNNER_TEMP:-/tmp}/stage0-fingerprint"
OUT="$WORK/out"
rm -rf "$WORK"
mkdir -p "$WORK/xapk" "$OUT"

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
[ -n "$SDK_ROOT" ] || { echo 'Android SDK root missing'; exit 2; }
yes | "$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --licenses >/dev/null 2>&1 || true
"$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --install "build-tools;$BT_VERSION" >/dev/null
APKSIGNER="$SDK_ROOT/build-tools/$BT_VERSION/apksigner"
[ -x "$APKSIGNER" ] || { echo 'Pinned Android build-tools unavailable'; exit 3; }

curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$WORK/NSS-Base.xapk"
echo "$EXPECTED_XAPK_SHA  $WORK/NSS-Base.xapk" | sha256sum -c -
unzip -tq "$WORK/NSS-Base.xapk" >/dev/null
unzip -q "$WORK/NSS-Base.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$EXPECTED_BASE_SHA  $BASE" | sha256sum -c -
[ -f "$WORK/xapk/manifest.json" ] || { echo 'XAPK manifest.json missing'; exit 4; }
cp "$WORK/xapk/manifest.json" "$OUT/xapk-manifest.json"
"$APKSIGNER" verify --verbose --print-certs "$BASE" > "$OUT/apksigner-certs.txt" 2>&1
cat "$OUT/apksigner-certs.txt"

python3 - "$WORK/NSS-Base.xapk" "$WORK/xapk" "$OUT/apksigner-certs.txt" "$OUT/NSS431_CANONICAL.json" "$EXPECTED_CERT_SHA1" <<'PY'
from pathlib import Path
import hashlib, json, re, sys, zipfile
xapk_path=Path(sys.argv[1]); xdir=Path(sys.argv[2]); certs=Path(sys.argv[3]).read_text(errors='replace'); out=Path(sys.argv[4]); expected_cert_sha1=sys.argv[5].lower()

def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def size(p): return Path(p).stat().st_size

def first_cert_digest(label):
    m=re.search(rf"certificate {re.escape(label)} digest:\s*([0-9a-fA-F: ]+)",certs)
    if not m: return None
    return re.sub(r'[^0-9a-fA-F]','',m.group(1)).lower()

meta=json.loads((xdir/'manifest.json').read_text(encoding='utf-8'))
package=meta.get('package_name') or meta.get('package') or meta.get('packageName')
version_code=meta.get('version_code') or meta.get('versionCode')
version_name=meta.get('version_name') or meta.get('versionName')
if not (package and version_code is not None and version_name):
    raise SystemExit(f'Could not parse XAPK package/version: keys={sorted(meta)}')
cert_sha256=first_cert_digest('SHA-256')
cert_sha1=first_cert_digest('SHA-1')
cert_dn_match=re.search(r"(?:V\d+(?:\.\d+)? Signer|Signer #\d+): certificate DN:\s*(.+)",certs)
if not cert_sha256 or not cert_sha1:
    raise SystemExit('Could not parse signer certificate; output preserved in apksigner-certs.txt')
if cert_sha1 != expected_cert_sha1:
    raise SystemExit(f'Unexpected signer SHA-1: {cert_sha1} != {expected_cert_sha1}')
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
 'package':str(package),
 'version_code':int(version_code),
 'version_name':str(version_name),
 'source':{
   'provider':'APKPure',
   'version_code':137,
   'url_template':'https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
 },
 'xapk':{'name':'NSS-Base.xapk','size':size(xapk_path),'sha256':sha256(xapk_path)},
 'base_apk':{
   **base,
   'signer_certificate_dn': cert_dn_match.group(1).strip() if cert_dn_match else None,
   'signer_certificate_sha256':cert_sha256,
   'signer_certificate_sha1':cert_sha1
 },
 'apk_entries':apks,
 'expected_xapk_entries':entries,
 'xapk_manifest_sha256':sha256(xdir/'manifest.json'),
 'toolchain_capture':{'android_build_tools':'37.0.0'}
}
if data['package']!='com.newstargames.newstarsoccer' or data['version_code']!=137 or data['version_name']!='4.31':
    raise SystemExit(f'Unexpected package/version: {data["package"]} {data["version_code"]} {data["version_name"]}')
out.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(out.read_text())
PY

cp "$OUT/NSS431_CANONICAL.json" "$GITHUB_WORKSPACE/NSS431_CANONICAL.json"
echo 'STAGE0_FINGERPRINT_CAPTURE_PASS'
