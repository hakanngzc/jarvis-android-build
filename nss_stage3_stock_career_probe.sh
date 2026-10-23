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
python3 tools/patch_cloud_startup_bypass_for_persistence_test.py "$WORK/base-ui-probe.apk" "$WORK/base-cloud-probe.apk"
python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe.apk"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android \
  -alias ci -dname 'CN=NSS Stage3 Public Runtime Probe' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1

sign_one(){
  local src="$1"
  local dst="$2"
  local aligned="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$aligned"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$aligned"
  "$APKSIGNER" verify --min-sdk-version 24 --verbose "$dst" >/dev/null
}

sign_one "$WORK/base-career-probe.apk" "$SIGNED/base.apk"
sign_one "$ROOT/config.tr.apk" "$SIGNED/config.tr.apk"
sign_one "$ROOT/config.xxhdpi.apk" "$SIGNED/config.xxhdpi.apk"
adb install-multiple -r "$SIGNED/base.apk" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true

fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  ! grep -qE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"
}

start_menu(){
  local i last
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb logcat -c >/dev/null 2>&1 || true
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  for i in $(seq 1 55); do
    sleep 1
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/start.log" 2>/dev/null || true
    last="$(grep -Ei 'SetActive:[[:space:]]*[A-Za-z0-9_]+' "$WORK/start.log" | tail -1 || true)"
    if grep -qiE 'SetActive:[[:space:]]*mainmenu' <<<"$last"; then
      echo "Stock MainMenu state active after ${i}s"
      return 0
    fi
  done
  cp "$WORK/start.log" "$OUT/start-menu-timeout.log" 2>/dev/null || true
  return 1
}

wait_rendered_menu(){
  local i png="$WORK/menu-render-probe.png" bytes
  for i in $(seq 1 60); do
    fatal_check || return 1
    adb exec-out screencap -p > "$png" 2>/dev/null || true
    bytes="$(wc -c < "$png" 2>/dev/null || echo 0)"
    # On this pinned API29/Pixel4 profile a blank white frame compresses to
    # ~17 KiB while the real stock menu is >1 MiB. Keep a conservative bound.
    if [ "$bytes" -gt 200000 ]; then
      cp "$png" "$OUT/stock-mainmenu-rendered.png"
      echo "Stock MainMenu rendered after ${i}s (${bytes} bytes)"
      return 0
    fi
    sleep 1
  done
  cp "$png" "$OUT/menu-render-timeout.png" 2>/dev/null || true
  echo 'Stock MainMenu state was active but a rendered frame was not observed'
  return 1
}

start_menu
wait_rendered_menu
adb shell wm size > "$OUT/wm-size.txt"
adb shell wm density > "$OUT/wm-density.txt"

# Visual evidence from run 39945433018 shows Play centered in this region on
# the pinned 1080x2280 Pixel4 profile. Wait for rendering before the tap.
PLAY_X=810
PLAY_Y=1450
adb logcat -c >/dev/null 2>&1 || true
adb shell input touchscreen tap "$PLAY_X" "$PLAY_Y" </dev/null || true

FOUND=0
for i in $(seq 1 20); do
  sleep 1
  fatal_check || exit 71
  adb logcat -d -v brief > "$OUT/career-tap.log" 2>/dev/null || true
  if grep -qiE 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' "$OUT/career-tap.log"; then
    FOUND=1
    break
  fi
done
adb exec-out screencap -p > "$OUT/after-play-tap.png" 2>/dev/null || true

if [ "$FOUND" -ne 1 ]; then
  echo 'CAREER_POINT_FOUND=NO'
  tail -80 "$OUT/career-tap.log" || true
  exit 72
fi

echo "$PLAY_X $PLAY_Y" > "$OUT/career-point.txt"
echo 'CAREER_POINT_FOUND=YES'
echo "CAREER_POINT=$(cat "$OUT/career-point.txt")"
echo 'VERDICT=STAGE3_STOCK_CAREER_DISCOVERY_PASS'
