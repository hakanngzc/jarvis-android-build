#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 6 ]; then
  echo "usage: $0 STOCK_BASE.apk STOCK_XAPK_DIR WORK_DIR OUT_DIR BAKSMALI.jar SMALI.jar" >&2
  exit 2
fi
BASE="$1"; XAPK_DIR="$2"; WORK="$3"; OUT="$4"; BAK="$5"; SMALI="$6"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
rm -rf "$WORK" "$OUT"
mkdir -p "$WORK/extract" "$WORK/smali3" "$WORK/fixtures" "$OUT/signed" "$OUT/evidence"

python3 - "$BASE" "$WORK/extract" <<'PY'
import sys,zipfile,pathlib
apk,out=sys.argv[1:]; out=pathlib.Path(out)
need={
 'classes3.dex':'classes3.dex',
 'assets/monkey/NewGUI/Common/ShieldAnims.uih':'ShieldAnims.uih',
 'assets/monkey/NewGUI/Atlases/Key.key':'Key.key',
}
with zipfile.ZipFile(apk) as z:
    for member,dst in need.items():
        try: data=z.read(member)
        except KeyError: raise SystemExit(f'missing stock member: {member}')
        (out/dst).write_bytes(data)
print('STAGE6_STOCK_MEMBERS_EXTRACTED=PASS')
PY

java -jar "$BAK" disassemble "$WORK/extract/classes3.dex" -o "$WORK/smali3"
CLUB_SMALI="$WORK/smali3/com/newstargames/newstarsoccer/c_TClub.smali"
[ -f "$CLUB_SMALI" ] || { echo "c_TClub.smali missing after baksmali" >&2; exit 31; }
cp "$CLUB_SMALI" "$WORK/evidence-stock-c_TClub.smali"
python3 "$ROOT/stage6_runtime/patch_club_badge_styles.py" "$CLUB_SMALI" "$WORK/c_TClub.patched.smali"
mv "$WORK/c_TClub.patched.smali" "$CLUB_SMALI"
cp "$CLUB_SMALI" "$OUT/evidence/c_TClub.patched.smali"
java -jar "$SMALI" assemble "$WORK/smali3" -o "$WORK/classes3-patched.dex"

python3 "$ROOT/stage6_runtime/patch_shield_ui.py" "$WORK/extract/ShieldAnims.uih" "$WORK/ShieldAnims.patched.uih"
python3 "$ROOT/stage6_runtime/generate_fixture_badges.py" "$WORK/fixtures"

python3 - "$BASE" "$WORK/base-stage6-unsigned.apk" "$WORK/classes3-patched.dex" "$WORK/ShieldAnims.patched.uih" "$WORK/fixtures/3141.png" "$WORK/fixtures/3163.png" <<'PY'
import sys,zipfile
src,dst,dex,ui,p3141,p3163=sys.argv[1:]
repl={
 'classes3.dex':open(dex,'rb').read(),
 'assets/monkey/NewGUI/Common/ShieldAnims.uih':open(ui,'rb').read(),
}
adds={
 'assets/monkey/NewGUI/RebornBadges/3141.png':open(p3141,'rb').read(),
 'assets/monkey/NewGUI/RebornBadges/3163.png':open(p3163,'rb').read(),
}
seen=set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w',allowZip64=True) as zout:
    for info in zin.infolist():
        if info.filename in adds:
            raise SystemExit(f'fixture path unexpectedly exists in stock APK: {info.filename}')
        data=zin.read(info.filename)
        if info.filename in repl:
            data=repl[info.filename]; seen.add(info.filename)
        zi=zipfile.ZipInfo(info.filename, info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0))
        zi.external_attr=info.external_attr; zi.create_system=info.create_system
        zi.flag_bits=info.flag_bits
        zout.writestr(zi,data,compress_type=info.compress_type,
                      compresslevel=9 if info.compress_type==zipfile.ZIP_DEFLATED else None)
    if seen != set(repl):
        raise SystemExit(f'missing replacement members: {set(repl)-seen}')
    for name,data in adds.items():
        zout.writestr(name,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
print('STAGE6_BASE_PATCHED=PASS')
PY

python3 "$ROOT/stage6_runtime/verify_fixture_apk.py" "$BASE" "$WORK/base-stage6-unsigned.apk" "$CLUB_SMALI" "$OUT/evidence/fixture-structure-unsigned.json"

BT="$(find "${ANDROID_HOME:?ANDROID_HOME required}/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
[ -x "$ZIPALIGN" ] && [ -x "$APKSIGNER" ] || { echo "Android signing tools missing under $BT" >&2; exit 32; }
keytool -genkeypair -noprompt -keystore "$WORK/stage6.keystore" -storepass android -keypass android -alias stage6 \
  -dname 'CN=NSS Stage6 Public Runtime' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/stage6.keystore" --ks-key-alias stage6 \
    --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-stage6-unsigned.apk" "$OUT/signed/base.apk"
for n in config.tr.apk config.xxhdpi.apk; do
  if [ -f "$XAPK_DIR/$n" ]; then sign_one "$XAPK_DIR/$n" "$OUT/signed/$n"; fi
done

python3 "$ROOT/stage6_runtime/verify_fixture_apk.py" "$BASE" "$OUT/signed/base.apk" "$CLUB_SMALI" "$OUT/evidence/fixture-structure-signed.json"
sha256sum "$OUT/signed/"*.apk > "$OUT/evidence/signed-apks.sha256"
printf 'STAGE6_FIXTURE_BUILD=PASS\n' | tee "$OUT/evidence/build-gates.txt"
