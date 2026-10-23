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
REPORT_DIR="$(dirname "$REPORT")"
REPORT_STEM="$(basename "$REPORT" .json)"
DIAG="$REPORT_DIR/${REPORT_STEM}-stock-m_CreateClub.smali.txt"
rm -rf "$WORK"
mkdir -p "$WORK/smali" "$WORK/verify" "$REPORT_DIR"

unzip -p "$BASE" classes3.dex > "$WORK/classes3-stock.dex"
[ -s "$WORK/classes3-stock.dex" ]
java -jar "$BAKSMALI_JAR" d "$WORK/classes3-stock.dex" -o "$WORK/smali"
TARGET="$WORK/smali/com/newstargames/newstarsoccer/c_TClub.smali"
[ -s "$TARGET" ]
cp "$TARGET" "$WORK/c_TClub-stock.smali"

# Persist only the exact target method into the uploaded evidence directory
# BEFORE attempting any patch. This makes anchor mismatches diagnosable without
# guessing at baksmali's register/literal formatting.
python3 - "$TARGET" "$DIAG" <<'PY'
import re,sys
src,out=sys.argv[1:]
text=open(src,encoding='utf-8').read()
m=re.search(r'(?ms)^\.method[^\n]*\bm_CreateClub\([^\n]*\n.*?^\.end method\s*$',text)
if not m:
    raise SystemExit('m_CreateClub method not found in stock baksmali output')
block=m.group(0)
open(out,'w',encoding='utf-8').write(block+'\n')
print('STOCK_M_CREATE_CLUB_DIAG=PASS lines='+str(len(block.splitlines())))
PY

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

# baksmali is free to choose register names. Verify the rebuilt DEX using the
# exact registers captured from the stock semantic anchor instead of fixed v12/v13.
python3 - "$VERIFY_TARGET" "$WORK/override-report.json" <<'PY'
import json,sys
smali_path,report_path=sys.argv[1:]
text=open(smali_path,encoding='utf-8').read()
r=json.load(open(report_path,encoding='utf-8'))
regs=r['captured_registers']; i=regs['id']; c=regs['club']; d=regs['divisor']
style='Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I'
required=[
    f'const/16 {d}, 0xc45', f'const/16 {i}, 0x10',
    f'const/16 {d}, 0xc55', f'const/16 {i}, 0x11',
    ':nss_reborn_badge_check_3157', ':nss_reborn_badge_done',
    f'rem-int/2addr {i}, {d}',
    f'iput {i}, {c}, {style}',
]
for needle in required:
    if needle not in text:
        raise SystemExit('rebuilt override verification missing: '+needle)
done=text.index(':nss_reborn_badge_done')
restored=text.find(f'const/16 {d}, 0xf',done)
if restored < 0:
    raise SystemExit('divisor register restore missing after override')
if not r.get('divisor_register_restored'):
    raise SystemExit('override report does not attest divisor restoration')
print('REBUILT_BADGE_OVERRIDE_VERIFY=PASS registers='+json.dumps(regs,sort_keys=True)+' divisor_restored=true')
PY

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
print('CLUB_BADGE_OVERRIDE_DEX=PASS classes3_only=changed fallback=id%15 overrides=3141:16,3157:17 divisor_restored=true')
PY
