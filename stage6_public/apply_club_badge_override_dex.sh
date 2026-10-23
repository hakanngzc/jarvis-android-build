#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 4 ]; then
  echo "usage: $0 BASE.apk OUT.apk WORK_DIR REPORT.json" >&2
  exit 2
fi
BASE="$1"; OUT="$2"; WORK="$3"; REPORT="$4"
: "${BAKSMALI_JAR:?BAKSMALI_JAR is required}"
: "${SMALI_JAR:?SMALI_JAR is required}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$WORK"
mkdir -p "$WORK/smali" "$WORK/verify"

unzip -p "$BASE" classes3.dex > "$WORK/classes3-stock.dex"
[ -s "$WORK/classes3-stock.dex" ]
java -jar "$BAKSMALI_JAR" d "$WORK/classes3-stock.dex" -o "$WORK/smali"
TARGET="$WORK/smali/com/newstargames/newstarsoccer/c_TClub.smali"
[ -s "$TARGET" ]
cp "$TARGET" "$WORK/c_TClub-stock.smali"
python3 "$ROOT/stage6_public/patch_club_badge_override.py" \
  "$TARGET" "$WORK/c_TClub-patched.smali" "$WORK/override-report.json"
mv "$WORK/c_TClub-patched.smali" "$TARGET"

BEFORE_CLASSES="$(find "$WORK/smali" -name '*.smali' -type f | wc -l | tr -d ' ')"
java -jar "$SMALI_JAR" a "$WORK/smali" -o "$WORK/classes3-patched.dex"
[ -s "$WORK/classes3-patched.dex" ]
java -jar "$BAKSMALI_JAR" d "$WORK/classes3-patched.dex" -o "$WORK/verify"
VERIFY_TARGET="$WORK/verify/com/newstargames/newstarsoccer/c_TClub.smali"
[ -s "$VERIFY_TARGET" ]
AFTER_CLASSES="$(find "$WORK/verify" -name '*.smali' -type f | wc -l | tr -d ' ')"
[ "$BEFORE_CLASSES" = "$AFTER_CLASSES" ]

grep -q 'const/16 v13, 0xc45' "$VERIFY_TARGET"
grep -q 'const/16 v12, 0x10' "$VERIFY_TARGET"
grep -q 'const/16 v13, 0xc55' "$VERIFY_TARGET"
grep -q 'const/16 v12, 0x11' "$VERIFY_TARGET"
grep -q ':nss_reborn_badge_check_3157' "$VERIFY_TARGET"
grep -q ':nss_reborn_badge_done' "$VERIFY_TARGET"
grep -q 'rem-int/2addr v12, v13' "$VERIFY_TARGET"

python3 - "$BASE" "$OUT" "$WORK/classes3-patched.dex" "$WORK/override-report.json" "$REPORT" "$BEFORE_CLASSES" <<'PY'
import hashlib,json,sys,zipfile
from pathlib import Path
src,dst,dex_path,override_path,report_path,class_count=sys.argv[1:]
src=Path(src); dst=Path(dst); dex_path=Path(dex_path)
newdex=dex_path.read_bytes(); override=json.load(open(override_path,encoding='utf-8'))
def sha(b): return hashlib.sha256(b).hexdigest()
def signature(n):
    u=n.upper()
    return u=='META-INF/MANIFEST.MF' or (u.startswith('META-INF/') and u.endswith(('.SF','.RSA','.DSA','.EC')))
with zipfile.ZipFile(src) as zin:
    olddex=zin.read('classes3.dex')
    dex_hashes_before={n:sha(zin.read(n)) for n in zin.namelist() if n.startswith('classes') and n.endswith('.dex')}
    infos=zin.infolist()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w',allowZip64=True) as zout:
    for info in infos:
        n=info.filename
        if signature(n): continue
        data=newdex if n=='classes3.dex' else zin.read(n)
        zi=zipfile.ZipInfo(n,info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0))
        zi.external_attr=info.external_attr; zi.create_system=info.create_system
        c=zipfile.ZIP_STORED if n=='resources.arsc' else info.compress_type
        zout.writestr(zi,data,compress_type=c,compresslevel=9 if c==zipfile.ZIP_DEFLATED else None)
with zipfile.ZipFile(dst) as z:
    dex_hashes_after={n:sha(z.read(n)) for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')}
assert sha(olddex)!=sha(newdex), 'classes3.dex did not change'
for n,h in dex_hashes_before.items():
    if n!='classes3.dex': assert dex_hashes_after.get(n)==h,(n,h,dex_hashes_after.get(n))
report={
  'source_apk_sha256':sha(src.read_bytes()),'patched_apk_sha256':sha(dst.read_bytes()),
  'classes3_sha256_before':sha(olddex),'classes3_sha256_after':sha(newdex),
  'other_dex_preserved':True,'smali_class_count_before':int(class_count),'smali_class_count_after':int(class_count),
  'override':override,
}
Path(report_path).parent.mkdir(parents=True,exist_ok=True)
Path(report_path).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print('CLUB_BADGE_OVERRIDE_DEX=PASS classes3_only=changed fallback=id%15 overrides=3141:16,3157:17')
PY
