#!/usr/bin/env bash
set -euo pipefail

PKG='com.newstargames.newstarsoccer'
OUT="$RUNNER_TEMP/stage3-update-ab"
WORK="$RUNNER_TEMP/stage3-update-work"
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
: > "$OUT/summary.txt"

URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$WORK/nss431.xapk"
echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c -
unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$BASE_SHA  $BASE" | sha256sum -c -

PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career.apk" | tee "$OUT/trial-patch.txt"
python3 stage3_tools/patch_first_run_overlays.py "$WORK/base-career.apk" "$WORK/base-career-overlay.apk" | tee "$OUT/overlay-patch.txt"
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_stage3_fast_match_probe.py "$WORK/base-career-overlay.apk" "$WORK/base-stage3.apk" | tee "$OUT/fast-match-patch.txt"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci -dname 'CN=NSS Stage3 Update AB' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$tmp"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-career-overlay.apk" "$WORK/signed/base-career.apk"
sign_one "$WORK/base-stage3.apk" "$WORK/signed/base-stage3.apk"
sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"
sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"

wait_start(){
  local tag="$1" result=TIMEOUT i
  adb logcat -c >/dev/null 2>&1 || true
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb shell am start -n "$PKG/.MonkeyGame" > "$OUT/$tag-am-start.txt"
  for i in $(seq 1 45); do
    sleep 1
    adb logcat -d -v threadtime > "$OUT/$tag-logcat.txt" 2>/dev/null || true
    if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$OUT/$tag-logcat.txt"; then result=MAINMENU; break; fi
    if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$OUT/$tag-logcat.txt"; then result=FATAL; break; fi
  done
  adb exec-out screencap -p > "$OUT/$tag-screen.png" 2>/dev/null || true
  echo "$tag RESULT=$result AFTER=${i}s" | tee -a "$OUT/summary.txt"
  grep -E 'OutOfMemoryError|growth limit|FATAL EXCEPTION|Process: com\.newstargames' "$OUT/$tag-logcat.txt" | tail -20 >> "$OUT/summary.txt" || true
  [ "$result" = MAINMENU ]
}

package_snapshot(){
  local tag="$1"
  adb shell dumpsys package "$PKG" > "$OUT/$tag-package.txt"
  grep -E 'versionCode=|versionName=|flags=|pkgFlags=|firstInstallTime=|lastUpdateTime=' "$OUT/$tag-package.txt" | head -30 >> "$OUT/summary.txt" || true
  if grep -q 'LARGE_HEAP' "$OUT/$tag-package.txt"; then echo "$tag LARGE_HEAP=YES" | tee -a "$OUT/summary.txt"; else echo "$tag LARGE_HEAP=NO" | tee -a "$OUT/summary.txt"; fi
}

adb uninstall "$PKG" >/dev/null 2>&1 || true
adb install-multiple "$WORK/signed/base-career.apk" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" | tee "$OUT/fresh-install.txt"
package_snapshot fresh
adb shell pm clear "$PKG" >/dev/null || true
wait_start fresh

# Critical A/B: no uninstall, same certificate, same splits, only base moves to Stage3 fast-match probe.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
adb install-multiple -r "$WORK/signed/base-stage3.apk" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" | tee "$OUT/update-install.txt"
package_snapshot update
wait_start update

cat "$OUT/summary.txt"
grep -q 'fresh LARGE_HEAP=YES' "$OUT/summary.txt"
grep -q 'fresh RESULT=MAINMENU' "$OUT/summary.txt"
grep -q 'update LARGE_HEAP=YES' "$OUT/summary.txt"
grep -q 'update RESULT=MAINMENU' "$OUT/summary.txt"
echo 'STAGE3_UPDATE_STARTUP_AB=PASS' | tee -a "$OUT/summary.txt"
