#!/usr/bin/env bash
set -euo pipefail

PKG=com.newstargames.newstarsoccer
WORK="$RUNNER_TEMP/nss-stage3-stock-career-probe"
OUT="$WORK/out"
XAPK="$WORK/stock.xapk"
ROOT="$WORK/xapk"
SIGNED="$WORK/signed"
mkdir -p "$ROOT" "$SIGNED" "$OUT"

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
EXPECTED_XAPK='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
EXPECTED_BASE='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$XAPK"
echo "$EXPECTED_XAPK  $XAPK" | sha256sum -c -
unzip -q "$XAPK" -d "$ROOT"
echo "$EXPECTED_BASE  $ROOT/com.newstargames.newstarsoccer.apk" | sha256sum -c -

# Near-stock interaction fixture: remove only first-run/privacy overlays. The
# stock main menu and all Java/DEX gameplay code remain untouched in this probe.
python3 - "$ROOT/com.newstargames.newstarsoccer.apk" "$WORK/base-ui-probe.apk" <<'PY'
import sys, zipfile
src,dst=sys.argv[1:]
repl={
 'assets/monkey/NewGUI/Screens/onboardingmain.uih': b'Rect:(0,0,0,0)\n    SetTweak(FirstPlayLocal,FirstPlayIncrement,4)\n',
 'assets/monkey/NewGUI/Screens/consent.uih': b'Macro:(M_Consent_Panel)\nEndM\nMacro:(M_Consent_Panel_ATT)\nEndM\n',
}
seen=set()
with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst,'w') as zout:
    for info in zin.infolist():
        data=zin.read(info.filename)
        if info.filename in repl:
            data=repl[info.filename]; seen.add(info.filename)
        zi=zipfile.ZipInfo(info.filename,info.date_time)
        zi.compress_type=info.compress_type; zi.comment=info.comment; zi.extra=info.extra
        zi.internal_attr=info.internal_attr; zi.external_attr=info.external_attr
        zi.create_system=info.create_system; zi.flag_bits=info.flag_bits
        zout.writestr(zi,data)
missing=set(repl)-seen
if missing: raise SystemExit(f'missing UI entries: {sorted(missing)}')
PY

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android \
  -alias ci -dname 'CN=NSS Stage3 Public Runtime Probe' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1

sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --min-sdk-version 24 --verbose "$dst" >/dev/null
}

sign_one "$WORK/base-ui-probe.apk" "$SIGNED/base.apk"
sign_one "$ROOT/config.tr.apk" "$SIGNED/config.tr.apk"
sign_one "$ROOT/config.xxhdpi.apk" "$SIGNED/config.xxhdpi.apk"
adb install-multiple -r "$SIGNED/base.apk" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true

fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  ! grep -qE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"
}

start_menu(){
  local i
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb logcat -c >/dev/null 2>&1 || true
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  for i in $(seq 1 55); do
    sleep 1
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/start.log" 2>/dev/null || true
    if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu' "$WORK/start.log"; then
      return 0
    fi
  done
  return 1
}

start_menu
adb exec-out screencap -p > "$OUT/stock-mainmenu.png"
adb shell wm size > "$OUT/wm-size.txt"
adb shell wm density > "$OUT/wm-density.txt"

# Candidate grid proven useful by the earlier stock touch-control. Restart the
# process after every miss so each attempt begins from a clean MainMenu state.
POINTS=(
  '810 850' '810 1000' '810 1150' '810 1300' '810 1450' '810 1600'
  '650 850' '650 1000' '650 1150' '650 1300' '650 1450' '650 1600'
  '500 850' '500 1000' '500 1150' '500 1300' '500 1450' '500 1600'
)
FOUND=0
N=0
: > "$OUT/career-probe-summary.txt"
for P in "${POINTS[@]}"; do
  N=$((N+1)); read -r X Y <<< "$P"
  start_menu
  adb logcat -c >/dev/null 2>&1 || true
  adb shell input touchscreen tap "$X" "$Y" </dev/null || true
  sleep 3
  adb logcat -d -v brief > "$OUT/probe-$N.log" 2>/dev/null || true
  adb exec-out screencap -p > "$OUT/probe-$N.png" 2>/dev/null || true
  LAST="$(grep -Ei 'Create Screen:|SetActive:|SETTING ACTIVE:' "$OUT/probe-$N.log" | tail -8 || true)"
  printf 'probe=%s point=%s,%s\n%s\n---\n' "$N" "$X" "$Y" "$LAST" >> "$OUT/career-probe-summary.txt"
  if grep -qiE 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' "$OUT/probe-$N.log"; then
    echo "$X $Y" > "$OUT/career-point.txt"
    FOUND=1
    break
  fi
done

adb logcat -d -v threadtime > "$OUT/final-logcat.txt" 2>/dev/null || true
fatal_check || { echo 'NSS-owned crash/ANR during stock career discovery'; exit 71; }
if [ "$FOUND" -ne 1 ]; then
  echo 'CAREER_POINT_FOUND=NO' | tee -a "$OUT/career-probe-summary.txt"
  exit 72
fi

echo 'CAREER_POINT_FOUND=YES' | tee -a "$OUT/career-probe-summary.txt"
echo "CAREER_POINT=$(cat "$OUT/career-point.txt")"
echo 'VERDICT=STAGE3_STOCK_CAREER_DISCOVERY_PASS'
