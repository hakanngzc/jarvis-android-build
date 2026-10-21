#!/usr/bin/env bash
set -euo pipefail

PKG='com.newstargames.newstarsoccer'
URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
EXPECTED_XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
EXPECTED_BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
EXPECTED_CERT_SHA1='eb94af17f8335fc62cff5a19517946c3dbdcaea8'
BT_VERSION='37.0.0'
WORK="${RUNNER_TEMP:-/tmp}/stage0-stock-byte-exact"
OUT="$WORK/out"
rm -rf "$WORK"
mkdir -p "$WORK/xapk" "$OUT"

curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$WORK/stock.xapk"
echo "$EXPECTED_XAPK_SHA  $WORK/stock.xapk" | sha256sum -c -
unzip -tq "$WORK/stock.xapk" >/dev/null
unzip -q "$WORK/stock.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$EXPECTED_BASE_SHA  $BASE" | sha256sum -c -

SDK_ROOT="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
"$SDK_ROOT/cmdline-tools/latest/bin/sdkmanager" --install "build-tools;$BT_VERSION" >/dev/null
APKSIGNER="$SDK_ROOT/build-tools/$BT_VERSION/apksigner"
"$APKSIGNER" verify --verbose --print-certs "$BASE" > "$OUT/original-signature.txt" 2>&1
grep -qi "$EXPECTED_CERT_SHA1" "$OUT/original-signature.txt"

# Install untouched publisher-signed bytes. No patching, zipalign or re-signing.
APKS=(
  "$BASE"
  "$WORK/xapk/config.tr.apk"
  "$WORK/xapk/config.xxhdpi.apk"
)
adb uninstall "$PKG" >/dev/null 2>&1 || true
adb install-multiple "${APKS[@]}" | tee "$OUT/install.txt"
adb shell pm clear "$PKG" >/dev/null 2>&1 || true
adb logcat -c >/dev/null 2>&1 || true
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb shell am start -n "$PKG/.MonkeyGame" | tee "$OUT/am-start.txt"

LIVE=0
for sec in 5 10 20 30; do
  sleep 5
  adb exec-out screencap -p > "$OUT/stock-${sec}s.png" 2>/dev/null || true
  adb logcat -d -v threadtime > "$OUT/logcat-${sec}s.txt" 2>/dev/null || true
  adb shell dumpsys activity activities > "$OUT/activity-${sec}s.txt" 2>/dev/null || true
  adb shell dumpsys window windows > "$OUT/window-${sec}s.txt" 2>/dev/null || true
  adb shell pidof "$PKG" > "$OUT/pid-${sec}s.txt" 2>/dev/null || true
  if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$OUT/logcat-${sec}s.txt"; then
    echo 'STAGE0_STOCK_BYTE_EXACT_RUNTIME_FATAL'
    exit 20
  fi
  if [ -s "$OUT/pid-${sec}s.txt" ] && grep -q "$PKG" "$OUT/activity-${sec}s.txt"; then LIVE=1; fi
done

adb shell dumpsys package "$PKG" > "$OUT/package.txt" 2>/dev/null || true
grep -q 'versionCode=137' "$OUT/package.txt"
grep -q 'versionName=4.31' "$OUT/package.txt"
[ "$LIVE" -eq 1 ] || { echo 'Stock process/activity never became live'; exit 21; }

cat > "$OUT/RESULT.txt" <<EOF
XAPK_SHA256=$EXPECTED_XAPK_SHA
BASE_APK_SHA256=$EXPECTED_BASE_SHA
PUBLISHER_CERT_SHA1=$EXPECTED_CERT_SHA1
APK_PATCHED=NO
APK_REALIGNED=NO
APK_RESIGNED=NO
PACKAGE=$PKG
VERSION_NAME=4.31
VERSION_CODE=137
PROCESS_ACTIVITY_LIVE=YES
NSS_OWNED_FATAL=NO
VERDICT=STAGE0_STOCK_BYTE_EXACT_BOOT_PASS
EOF
cat "$OUT/RESULT.txt"
