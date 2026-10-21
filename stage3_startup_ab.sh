#!/usr/bin/env bash
set -euo pipefail

PKG='com.newstargames.newstarsoccer'
OUT="$RUNNER_TEMP/stage3-startup-ab"
WORK="$RUNNER_TEMP/stage3-startup-work"
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'

curl -fL --retry 3 -A 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/141 Safari/537.36' -e "$REFERER" "$URL" -o "$WORK/nss431.xapk"
echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c -
unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$BASE_SHA  $BASE" | sha256sum -c -

PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/repack_apk_preserve.py "$BASE" "$WORK/base-repack.apk"
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-trial.apk" | tee "$OUT/trial-patch.txt"
python3 stage3_tools/patch_first_run_overlays.py "$WORK/base-trial.apk" "$WORK/base-trial-overlay.apk" | tee "$OUT/overlay-patch.txt"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"; APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci -dname 'CN=NSS Stage3 Startup AB' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){ local src="$1" dst="$2"; local tmp="$WORK/aligned-$(basename "$dst")"; "$ZIPALIGN" -f 4 "$src" "$tmp"; "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"; "$APKSIGNER" verify --verbose "$dst" >/dev/null; }
sign_one "$WORK/base-repack.apk" "$WORK/signed/base-repack.apk"
sign_one "$WORK/base-trial.apk" "$WORK/signed/base-trial.apk"
sign_one "$WORK/base-trial-overlay.apk" "$WORK/signed/base-trial-overlay.apk"
sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"
sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"

run_variant(){
  local name="$1" base="$2"
  echo "===== VARIANT $name =====" | tee -a "$OUT/summary.txt"
  adb uninstall "$PKG" >/dev/null 2>&1 || true
  adb install-multiple -r "$base" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" > "$OUT/$name-install.txt"
  adb shell dumpsys package "$PKG" > "$OUT/$name-package.txt"
  grep -E 'versionCode=|versionName=|flags=|pkgFlags=' "$OUT/$name-package.txt" | head -20 | tee -a "$OUT/summary.txt"
  if grep -q 'LARGE_HEAP' "$OUT/$name-package.txt"; then echo "$name LARGE_HEAP=YES" | tee -a "$OUT/summary.txt"; else echo "$name LARGE_HEAP=NO" | tee -a "$OUT/summary.txt"; fi
  adb shell pm clear "$PKG" >/dev/null || true
  adb logcat -c || true
  adb shell am start -n "$PKG/.MonkeyGame" > "$OUT/$name-am-start.txt"
  local result=TIMEOUT i
  for i in $(seq 1 60); do
    sleep 1
    adb logcat -d -v threadtime > "$OUT/$name-logcat.txt" 2>/dev/null || true
    if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$OUT/$name-logcat.txt"; then result=MAINMENU; break; fi
    if grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$OUT/$name-logcat.txt"; then result=FATAL; break; fi
  done
  adb exec-out screencap -p > "$OUT/$name-screen.png" 2>/dev/null || true
  echo "$name RESULT=$result AFTER=${i}s" | tee -a "$OUT/summary.txt"
  grep -E 'OutOfMemoryError|growth limit|FATAL EXCEPTION|Process: com\.newstargames' "$OUT/$name-logcat.txt" | tail -20 >> "$OUT/summary.txt" || true
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
}

run_variant repack "$WORK/signed/base-repack.apk"
run_variant trial "$WORK/signed/base-trial.apk"
run_variant trial-overlay "$WORK/signed/base-trial-overlay.apk"

cat "$OUT/summary.txt"
# Diagnostic gate: workflow itself succeeds if all three variants were observed.
grep -q 'repack RESULT=' "$OUT/summary.txt"
grep -q 'trial RESULT=' "$OUT/summary.txt"
grep -q 'trial-overlay RESULT=' "$OUT/summary.txt"
