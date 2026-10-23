#!/usr/bin/env python3
from pathlib import Path

SOURCE = Path('stage1_public/runtime_gate_v2.sh')
OUTPUT = Path('stage5_public/runtime_name_save_compat.sh')

STAGE5_BLOCK = '''record STAGE5_STOCK_CAREER_CREATED PASS

# ---------------------------------------------------------------------------
# Stage5: old-save compatibility across a same-signed name-only data update.
# ---------------------------------------------------------------------------
PREF='/data/data/com.newstargames.newstarsoccer/shared_prefs/MonkeyGame.xml'
PATCHED_SHORTNAME='Beşiktaş REBORN'

adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb root >/dev/null 2>&1 || true
adb wait-for-device
sleep 1
adb shell test -f "$PREF"
adb shell cat "$PREF" > "$OUT/stage5-save-before-update.xml"
SAVE_BEFORE_SHA="$(sha256sum "$OUT/stage5-save-before-update.xml" | awk '{print $1}')"
record stage5_save_before_sha256 "$SAVE_BEFORE_SHA"

python3 - "$WORK/base-test-unsigned.apk" "$WORK/base-namepatch-unsigned.apk" \\
  "$OUT/stage5-name-patch-report.json" "$PATCHED_SHORTNAME" <<'PY'
import hashlib,json,sys,zipfile
src,dst,report_path,new_name=sys.argv[1:]
asset='assets/monkey/MyData/v2025/Clubs.txt'
target='3141'
refs=('nationid','leagueid','continentalcompid','bteamof')
with zipfile.ZipFile(src) as zin:
    raw=zin.read(asset).decode('utf-8-sig')
lines=raw.splitlines(keepends=True)
if not lines:
    raise SystemExit('empty Clubs.txt')
header=lines[0].rstrip('\\r\\n').split('\\t')
for required in ('id','shortname',*refs):
    if required not in header:
        raise SystemExit(f'missing Clubs.txt column: {required}')
id_i=header.index('id'); name_i=header.index('shortname')
ref_i={k:header.index(k) for k in refs}
def ids(text_lines):
    out=[]
    for line in text_lines[1:]:
        body=line.rstrip('\\r\\n')
        cells=body.split('\\t')
        if id_i >= len(cells): continue
        try: out.append(int(cells[id_i].strip()))
        except Exception: pass
    return out
before_ids=ids(lines)
hits=[]
old_name=None
old_refs=None
for pos,line in enumerate(lines[1:],1):
    if line.endswith('\\r\\n'): ending='\\r\\n'; body=line[:-2]
    elif line.endswith('\\n'): ending='\\n'; body=line[:-1]
    elif line.endswith('\\r'): ending='\\r'; body=line[:-1]
    else: ending=''; body=line
    cells=body.split('\\t')
    if id_i < len(cells) and cells[id_i].strip()==target:
        hits.append(pos)
        old_name=cells[name_i]
        old_refs={k:cells[i] for k,i in ref_i.items()}
        if old_name != 'Beşiktaş':
            raise SystemExit(f'unexpected stock shortname for {target}: {old_name!r}')
        cells[name_i]=new_name
        lines[pos]='\\t'.join(cells)+ending
if len(hits)!=1:
    raise SystemExit(f'expected one club {target}, got {hits}')
after_ids=ids(lines)
if before_ids != after_ids:
    raise SystemExit('numeric club ID order changed')
new_raw=''.join(lines).encode('utf-8-sig')
new_text=new_raw.decode('utf-8-sig')
new_lines=new_text.splitlines()
target_line=[x for x in new_lines[1:] if x.split('\\t')[id_i].strip()==target]
if len(target_line)!=1:
    raise SystemExit('patched target row missing')
new_cells=target_line[0].split('\\t')
new_refs={k:new_cells[i] for k,i in ref_i.items()}
if new_refs != old_refs:
    raise SystemExit('persistent reference columns changed')
if new_cells[name_i] != new_name:
    raise SystemExit('patched shortname not stored')
seen=False
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w',allowZip64=True) as zout:
    for info in zin.infolist():
        data=zin.read(info.filename)
        if info.filename==asset:
            data=new_raw; seen=True
        zi=zipfile.ZipInfo(info.filename, info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0))
        zi.external_attr=info.external_attr; zi.create_system=info.create_system
        zout.writestr(zi,data,compress_type=info.compress_type,
                      compresslevel=9 if info.compress_type==zipfile.ZIP_DEFLATED else None)
if not seen:
    raise SystemExit('Clubs.txt asset not written')
report={
  'club_id':int(target),
  'changed_columns':['shortname'],
  'shortname_before':old_name,
  'shortname_after':new_name,
  'numeric_id_order_preserved':True,
  'persistent_references_preserved':True,
  'persistent_references':old_refs,
  'clubs_asset_sha256_before':hashlib.sha256(raw.encode('utf-8-sig')).hexdigest(),
  'clubs_asset_sha256_after':hashlib.sha256(new_raw).hexdigest(),
  'old_save_id_resolution_contract':'preserved',
}
open(report_path,'w',encoding='utf-8').write(json.dumps(report,indent=2,ensure_ascii=False)+'\\n')
print('STAGE5_NAME_PATCH_BUILD=PASS',json.dumps(report,ensure_ascii=False))
PY
record STAGE5_PATCH_ID_CONTRACT PASS

sign_one "$WORK/base-namepatch-unsigned.apk" "$WORK/signed/base-namepatch.apk"
UPDATE_APKS=("$WORK/signed/base-namepatch.apk")
[ -f "$WORK/signed/config.tr.apk" ] && UPDATE_APKS+=("$WORK/signed/config.tr.apk")
[ -f "$WORK/signed/config.xxhdpi.apk" ] && UPDATE_APKS+=("$WORK/signed/config.xxhdpi.apk")
adb install-multiple -r "${UPDATE_APKS[@]}" | tee "$OUT/stage5-update-install.txt"

adb root >/dev/null 2>&1 || true
adb wait-for-device
sleep 1
adb shell cat "$PREF" > "$OUT/stage5-save-after-update.xml"
SAVE_AFTER_SHA="$(sha256sum "$OUT/stage5-save-after-update.xml" | awk '{print $1}')"
record stage5_save_after_update_sha256 "$SAVE_AFTER_SHA"
if [ "$SAVE_AFTER_SHA" != "$SAVE_BEFORE_SHA" ]; then
  record STAGE5_SAVE_UNCHANGED_AFTER_UPDATE FAIL
  exit 131
fi
record STAGE5_SAVE_UNCHANGED_AFTER_UPDATE PASS

INSTALLED_BASE="$(adb shell pm path "$PKG" | sed -n 's/^package://p' | head -1 | tr -d '\\r')"
adb exec-out cat "$INSTALLED_BASE" > "$WORK/installed-namepatch-base.apk"
python3 - "$WORK/installed-namepatch-base.apk" "$PATCHED_SHORTNAME" <<'PY'
import sys,zipfile
apk,new_name=sys.argv[1:]
asset='assets/monkey/MyData/v2025/Clubs.txt'
with zipfile.ZipFile(apk) as z:
    raw=z.read(asset).decode('utf-8-sig')
lines=raw.splitlines()
header=lines[0].split('\\t')
id_i=header.index('id'); name_i=header.index('shortname')
hits=[]
for line in lines[1:]:
    cells=line.split('\\t')
    if id_i < len(cells) and cells[id_i].strip()=='3141':
        hits.append(cells[name_i])
if hits != [new_name]:
    raise SystemExit(f'installed club 3141 mismatch: {hits!r}')
print('STAGE5_PATCHED_TABLE_INSTALLED=PASS club_id=3141 shortname='+new_name)
PY
record STAGE5_PATCHED_TABLE_INSTALLED PASS

manual_load_slot 0 stage5-postpatch
record STAGE5_OLD_SAVE_LOAD PASS
fatal_check
record STAGE5_NAME_SAVE_COMPAT PASS
echo 'VERDICT=STAGE5_PUBLIC_NAME_SAVE_COMPAT_PASS'
exit 0'''


def inject_stage5(source: str) -> str:
    anchor = 'create_career 0 slot0-seed\ncreate_career 1 slot1\n'
    if source.count(anchor) != 1:
        raise ValueError(f'stage5 insertion anchor expected once, got {source.count(anchor)}')
    source = source.replace(
        'OUT="$ROOT/stage1_public_artifacts/runtime"',
        'OUT="$ROOT/stage5_public_artifacts/runtime"',
        1,
    )
    source = source.replace(
        'WORK="$RUNNER_TEMP/nss-stage1-residual"',
        'WORK="$RUNNER_TEMP/nss-stage5-name-save-compat"',
        1,
    )
    source = source.replace(
        'SUMMARY="$OUT/residual-gates.txt"',
        'SUMMARY="$OUT/stage5-gates.txt"',
        1,
    )
    replacement = 'create_career 0 slot0-seed\n' + STAGE5_BLOCK + '\n\ncreate_career 1 slot1\n'
    return source.replace(anchor, replacement, 1)


def main():
    source = SOURCE.read_text(encoding='utf-8')
    output = inject_stage5(source)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(output, encoding='utf-8')
    print(
        'STAGE5_GATE_BUILDER=PASS '
        'anchor=slot0-postsave '
        'patch=club3141-shortname-only '
        'old-save-update-load=enabled'
    )


if __name__ == '__main__':
    main()
