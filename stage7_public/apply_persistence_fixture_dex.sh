#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 5 ]; then
  echo "usage: $0 BASE.apk OUT.apk WORK_DIR MODE REPORT.json" >&2
  exit 2
fi
BASE="$1"; OUT="$2"; WORK="$3"; MODE="$4"; REPORT="$5"
case "$MODE" in mutator|verifier) ;; *) echo "MODE must be mutator or verifier" >&2; exit 2;; esac
: "${BAKSMALI_JAR:?BAKSMALI_JAR is required}"
: "${SMALI_JAR:?SMALI_JAR is required}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPORT_DIR="$(dirname "$REPORT")"; STEM="$(basename "$REPORT" .json)"
rm -rf "$WORK"; mkdir -p "$WORK/smali" "$WORK/verify" "$REPORT_DIR"

unzip -p "$BASE" classes3.dex > "$WORK/classes3-stock.dex"
test -s "$WORK/classes3-stock.dex"
java -jar "$BAKSMALI_JAR" d "$WORK/classes3-stock.dex" -o "$WORK/smali"
TARGET="$WORK/smali/com/newstargames/newstarsoccer/c_TPlayer.smali"
test -s "$TARGET"
cp "$TARGET" "$WORK/c_TPlayer-stock.smali"

python3 - "$TARGET" "$MODE" "$WORK/patch-meta.json" <<'PY'
import json,sys
from pathlib import Path
sys.path.insert(0,'stage7_public')
from persistence_fixture_patch import patch_mutator_text,patch_verifier_text
path,mode,meta_path=sys.argv[1:]
text=Path(path).read_text(encoding='utf-8')
if mode=='mutator': out,meta=patch_mutator_text(text)
else: out,meta=patch_verifier_text(text)
Path(path).write_text(out,encoding='utf-8')
meta['mode']=mode
Path(meta_path).write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
print(f'STAGE7_SMALI_PATCH=PASS mode={mode} method={meta["method"]} locals={meta["old_locals"]}->{meta["new_locals"]}')
PY

BEFORE_CLASSES="$(find "$WORK/smali" -name '*.smali' -type f | wc -l | tr -d ' ')"
java -jar "$SMALI_JAR" a "$WORK/smali" -o "$WORK/classes3-patched.dex"
test -s "$WORK/classes3-patched.dex"
java -jar "$BAKSMALI_JAR" d "$WORK/classes3-patched.dex" -o "$WORK/verify"
VERIFY="$WORK/verify/com/newstargames/newstarsoccer/c_TPlayer.smali"
test -s "$VERIFY"
AFTER_CLASSES="$(find "$WORK/verify" -name '*.smali' -type f | wc -l | tr -d ' ')"
test "$BEFORE_CLASSES" = "$AFTER_CLASSES"

python3 - "$VERIFY" "$MODE" "$WORK/patch-meta.json" "$REPORT_DIR/${STEM}-rebuilt-target.smali.txt" <<'PY'
import json,re,sys
from pathlib import Path
src,mode,meta_path,out=sys.argv[1:]
text=Path(src).read_text(encoding='utf-8'); meta=json.load(open(meta_path,encoding='utf-8'))
name='p_SaveCareer' if mode=='mutator' else 'm_LoadCareer'
m=re.search(r'(?ms)^\.method[^\n]*\b'+re.escape(name)+r'\(\)V\n.*?^\.end method\s*$',text)
if not m: raise SystemExit('rebuilt target method missing: '+name)
block=m.group(0); Path(out).write_text(block+'\n',encoding='utf-8')
if mode=='mutator':
    req=['STAGE7_TEST_MUTATOR_BEGIN','->m_bank:I','->m_wage:I','->m_goalbonus:I','->m_assistbonus:I','->m_relationboss:F','->m_relationsponsors:F','->m_spenttime:I','->m_gambling:I','->m_technique:[I','->m_pace:[I','->m_vision:[I','->m_setpieces:[I','->m_power:[I','->m_donetraining:I','->m_trainingattempts:I']
    if block.count('STAGE7_TEST_MUTATOR_BEGIN')!=1: raise SystemExit('mutator marker count invalid')
else:
    req=['STAGE7_TEST_VERIFY_RESAVE_BEGIN','Lcom/newstargames/newstarsoccer/bb_;->g_player:','Lcom/newstargames/newstarsoccer/c_TPlayer;->p_SaveCareer()V']
    if block.count('STAGE7_TEST_VERIFY_RESAVE_BEGIN')!=1: raise SystemExit('verifier marker count invalid')
for needle in req:
    if needle not in block: raise SystemExit('rebuilt semantic verification missing: '+needle)
print(f'STAGE7_REBUILT_VERIFY=PASS mode={mode} method={name} marker_count=1')
PY

python3 - "$BASE" "$OUT" "$WORK/classes3-patched.dex" "$WORK/patch-meta.json" "$REPORT" "$MODE" "$BEFORE_CLASSES" <<'PY'
import hashlib,json,sys,zipfile
from pathlib import Path
src,dst,dex_path,meta_path,report_path,mode,class_count=sys.argv[1:]
src=Path(src); dst=Path(dst); newdex=Path(dex_path).read_bytes(); meta=json.load(open(meta_path,encoding='utf-8'))
def sha(b): return hashlib.sha256(b).hexdigest()
def sig(n):
    u=n.upper(); return u=='META-INF/MANIFEST.MF' or (u.startswith('META-INF/') and u.endswith(('.SF','.RSA','.DSA','.EC')))
with zipfile.ZipFile(src) as z:
    infos=z.infolist(); olddex=z.read('classes3.dex'); before={n:sha(z.read(n)) for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')}
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w',allowZip64=True) as zout:
    for info in infos:
        n=info.filename
        if sig(n): continue
        data=newdex if n=='classes3.dex' else zin.read(n)
        zi=zipfile.ZipInfo(n,info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0)); zi.external_attr=info.external_attr; zi.create_system=info.create_system
        c=zipfile.ZIP_STORED if n=='resources.arsc' else info.compress_type
        zout.writestr(zi,data,compress_type=c,compresslevel=9 if c==zipfile.ZIP_DEFLATED else None)
with zipfile.ZipFile(dst) as z: after={n:sha(z.read(n)) for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')}
assert sha(olddex)!=sha(newdex),'classes3.dex did not change'
for n,h in before.items():
    if n!='classes3.dex': assert after.get(n)==h,(n,h,after.get(n))
report={'mode':mode,'source_apk_sha256':sha(src.read_bytes()),'patched_apk_sha256':sha(dst.read_bytes()),'classes3_sha256_before':sha(olddex),'classes3_sha256_after':sha(newdex),'other_dex_preserved':True,'smali_class_count_before':int(class_count),'smali_class_count_after':int(class_count),'patch':meta}
Path(report_path).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(f'STAGE7_FIXTURE_DEX=PASS mode={mode} classes3_only=changed')
PY
