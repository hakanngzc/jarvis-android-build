#!/usr/bin/env bash
set -euo pipefail

OUT="$RUNNER_TEMP/nss431-kvm-smoke"
mkdir -p "$OUT/xapk"
URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
PKG='com.newstargames.newstarsoccer'

curl -fL --retry 3 \
  -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' \
  -e "$REFERER" \
  "$URL" -o "$OUT/nss431.xapk"

echo 'afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e  '"$OUT/nss431.xapk" | sha256sum -c -
unzip -q "$OUT/nss431.xapk" -d "$OUT/xapk"
echo '46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4  '"$OUT/xapk/com.newstargames.newstarsoccer.apk" | sha256sum -c -

adb install-multiple -r \
  "$OUT/xapk/com.newstargames.newstarsoccer.apk" \
  "$OUT/xapk/config.tr.apk" \
  "$OUT/xapk/config.xxhdpi.apk"

adb shell dumpsys package "$PKG" > "$OUT/package.txt"
grep -q 'versionCode=137' "$OUT/package.txt"
grep -q 'versionName=4.31' "$OUT/package.txt"

adb logcat -c || true
adb shell am start -n "$PKG/.MonkeyGame" > "$OUT/am-start.txt"

: > "$OUT/verdict.txt"
for i in $(seq 1 60); do
  sleep 1
  adb logcat -d -v brief > "$OUT/logcat.txt" || true
  if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$OUT/logcat.txt"; then
    echo "MAINMENU_REACHED_AFTER=${i}s" | tee -a "$OUT/verdict.txt"
    break
  fi
  if grep -qiE 'FATAL EXCEPTION.*newstarsoccer|Process: com\.newstargames\.newstarsoccer|ANR in com\.newstargames\.newstarsoccer' "$OUT/logcat.txt"; then
    echo 'NSS_RUNTIME_FATAL' | tee -a "$OUT/verdict.txt"
    exit 41
  fi
done

sleep 5
adb exec-out screencap -p > "$OUT/screen.png" || true
adb shell dumpsys activity activities > "$OUT/activity.txt" || true
pidof=$(adb shell pidof "$PKG" | tr -d '\r' || true)
echo "PID=$pidof" >> "$OUT/verdict.txt"
test -n "$pidof"
grep -q 'MAINMENU_REACHED' "$OUT/verdict.txt"
echo 'NSS431_KVM_SMOKE=PASS' | tee -a "$OUT/verdict.txt"
