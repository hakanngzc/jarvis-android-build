#!/usr/bin/env bash
set -euo pipefail
OUT="$RUNNER_TEMP/nss431-nav-probe"
mkdir -p "$OUT/xapk"
URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
PKG='com.newstargames.newstarsoccer'
curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$OUT/nss431.xapk"
echo 'afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e  '"$OUT/nss431.xapk" | sha256sum -c -
unzip -q "$OUT/nss431.xapk" -d "$OUT/xapk"
echo '46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4  '"$OUT/xapk/com.newstargames.newstarsoccer.apk" | sha256sum -c -
adb install-multiple -r "$OUT/xapk/com.newstargames.newstarsoccer.apk" "$OUT/xapk/config.tr.apk" "$OUT/xapk/config.xxhdpi.apk"
adb logcat -c || true
adb shell am start -n "$PKG/.MonkeyGame" > "$OUT/am-start.txt"
for i in $(seq 1 60); do
  sleep 1
  adb logcat -d -v brief > "$OUT/logcat.txt" || true
  if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$OUT/logcat.txt"; then
    echo "MAINMENU_REACHED_AFTER=${i}s" > "$OUT/verdict.txt"
    break
  fi
done
sleep 10
adb exec-out screencap -p > "$OUT/mainmenu.png"
adb shell dumpsys activity activities > "$OUT/activity.txt" || true
pidof=$(adb shell pidof "$PKG" | tr -d '\r' || true)
echo "PID=$pidof" >> "$OUT/verdict.txt"
test -n "$pidof"
grep -q MAINMENU_REACHED "$OUT/verdict.txt"
echo NAV_PROBE_PASS >> "$OUT/verdict.txt"
