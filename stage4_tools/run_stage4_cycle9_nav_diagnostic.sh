#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: run_stage4_cycle9_nav_diagnostic.sh COMPOSED_GATE" >&2
  exit 2
fi

GATE="$1"
PKG=com.newstargames.newstarsoccer
DIAG_OUT="${RUNNER_TEMP:?}/stage4-cycle9-diagnostic"
DIAG_WORK="$RUNNER_TEMP/stage4-cycle9-diagnostic-work"
DIAG_FLOW="$DIAG_OUT/STAGE4_CYCLE9_NAV_DIAGNOSTIC.log"
URL='https://d.apkpure.net/b/XAPK/com.newstargames.newstarsoccer?versionCode=137'
REFERER='https://apkpure.net/new-star-soccer/com.newstargames.newstarsoccer/download/4.31'
XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
RUN262_ARTIFACT_ID=12647883054

mkdir -p "$DIAG_OUT" "$DIAG_WORK"

# Load the exact composed Stage4 navigation helpers without executing the normal
# fresh-Career main body, then restore diagnostic-local output/work paths.
awk '/^# Exact stock source/{exit} {print}' "$GATE" > "$DIAG_WORK/helpers.sh"
# shellcheck disable=SC1090
source "$DIAG_WORK/helpers.sh"
OUT="$DIAG_OUT"
WORK="$DIAG_WORK"
FLOW="$DIAG_FLOW"
mkdir -p "$OUT" "$WORK/xapk" "$WORK/signed"
: > "$FLOW"

exact_source=0
for attempt in 1 2 3; do
  rm -f "$WORK/nss431.xapk"
  echo "source download attempt $attempt/3" | tee -a "$FLOW"
  curl -fL --retry 3 -A 'Mozilla/5.0' -e "$REFERER" "$URL" -o "$WORK/nss431.xapk"
  if echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c - >> "$FLOW" 2>&1; then
    exact_source=1
    break
  fi
  echo "source sha mismatch attempt $attempt/3" | tee -a "$FLOW"
  sleep 2
done
[ "$exact_source" -eq 1 ] || { echo 'exact stock XAPK unavailable' | tee -a "$FLOW"; exit 1; }

unzip -q "$WORK/nss431.xapk" -d "$WORK/xapk"
BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"
echo "$BASE_SHA  $BASE" | sha256sum -c - | tee -a "$FLOW"
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" >> "$FLOW"
python3 stage3_tools/patch_first_run_overlays.py "$WORK/base-career-unsigned.apk" "$WORK/base-natural-unsigned.apk" >> "$FLOW"

BT="$(find "$ANDROID_HOME/build-tools" -mindepth 1 -maxdepth 1 -type d | sort -V | tail -1)"
ZIPALIGN="$BT/zipalign"
APKSIGNER="$BT/apksigner"
keytool -genkeypair -noprompt -keystore "$WORK/ci.keystore" -storepass android -keypass android -alias ci -dname 'CN=NSS Stage4 Diagnostic CI' -keyalg RSA -keysize 2048 -validity 3650 >/dev/null 2>&1
sign_one(){
  local src="$1" dst="$2" tmp
  tmp="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$tmp"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}
sign_one "$WORK/base-natural-unsigned.apk" "$WORK/signed/base-natural.apk"
sign_one "$WORK/xapk/config.tr.apk" "$WORK/signed/config.tr.apk"
sign_one "$WORK/xapk/config.xxhdpi.apk" "$WORK/signed/config.xxhdpi.apk"
adb install-multiple -r "$WORK/signed/base-natural.apk" "$WORK/signed/config.tr.apk" "$WORK/signed/config.xxhdpi.apk" >/dev/null

curl -fL \
  -H "Authorization: Bearer ${GITHUB_TOKEN:?}" \
  -H 'Accept: application/vnd.github+json' \
  -H 'X-GitHub-Api-Version: 2022-11-28' \
  "https://api.github.com/repos/hakanngzc/jarvis-android-build/actions/artifacts/${RUN262_ARTIFACT_ID}/zip" \
  -o "$WORK/run262.zip"
unzip -q "$WORK/run262.zip" -d "$WORK/run262"
SAVE_XML="$(find "$WORK/run262" -type f -name 'cycle-9-MonkeyGame.xml' | head -1)"
[ -n "$SAVE_XML" ] && [ -s "$SAVE_XML" ] || { echo 'cycle-9 save missing' | tee -a "$FLOW"; exit 1; }
echo "cycle9 save bytes=$(wc -c < "$SAVE_XML")" | tee -a "$FLOW"

adb shell pm clear "$PKG" >/dev/null || true
adb root >/dev/null 2>&1 || true
adb wait-for-device
sleep 2
adb shell mkdir -p "/data/data/$PKG/shared_prefs"
adb push "$SAVE_XML" /data/local/tmp/MonkeyGame.xml >/dev/null
uid="$(adb shell dumpsys package "$PKG" | tr -d '\r' | sed -n 's/.*userId=\([0-9][0-9]*\).*/\1/p' | head -1)"
[[ "$uid" =~ ^[0-9]+$ ]] || { echo 'package uid unavailable' | tee -a "$FLOW"; exit 1; }
adb shell cp /data/local/tmp/MonkeyGame.xml "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell chown "$uid:$uid" "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell chmod 660 "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
adb shell restorecon "/data/data/$PKG/shared_prefs/MonkeyGame.xml" >/dev/null 2>&1 || true

clear_log
adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
sleep 5
adb logcat -d -v brief > "$WORK/start.txt" 2>/dev/null || true
if grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/start.txt"; then
  echo 'cycle9 save auto-loaded to GameMenu' | tee -a "$FLOW"
elif grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$WORK/start.txt"; then
  echo 'cycle9 save reached MainMenu; loading slot0 through stock UI' | tee -a "$FLOW"
  open_slot0 cycle9-diagnostic
  load_existing cycle9-diagnostic
else
  cp "$WORK/start.txt" "$OUT/start-state.txt"
  shot cycle9-start-unknown
  echo 'cycle9 save reached neither GameMenu nor MainMenu' | tee -a "$FLOW"
  exit 1
fi

capture_log 'cycle9 diagnostic loaded'
clear_log
if ! navigate_until_match; then
  capture_log 'cycle9 diagnostic navigate failed'
  shot cycle10-navigation-failed
  echo 'STAGE4_CYCLE9_NAV_DIAGNOSTIC_FAIL' | tee -a "$FLOW"
  exit 1
fi
capture_log 'cycle9 diagnostic reached Match'
shot cycle10-match-reached

grep -qi 'information' "$FLOW" || { echo 'information surface not exercised' | tee -a "$FLOW"; exit 1; }
grep -qi 'PurchaseAnim' "$FLOW" || { echo 'PurchaseAnim surface not exercised' | tee -a "$FLOW"; exit 1; }
echo 'STAGE4_CYCLE9_NAV_DIAGNOSTIC_PASS' | tee -a "$FLOW"
