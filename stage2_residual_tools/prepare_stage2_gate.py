#!/usr/bin/env python3
from __future__ import annotations
import re
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding='utf-8')

replacements = [
    (
        '''fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qiE 'ANR in com\\.newstargames\\.newstarsoccer|Process: com\\.newstargames\\.newstarsoccer, PID:|FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'; return 1
  fi
}''',
        '''fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qiE 'Process: com\\.newstargames\\.newstarsoccer, PID:|FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash detected'; return 1
  fi
  if grep -qi 'ANR in com.newstargames.newstarsoccer' "$WORK/live-logcat.txt"; then
    if grep -qi 'Reason: executing service com.newstargames.newstarsoccer/com.google.android.gms.measurement.AppMeasurementService' "$WORK/live-logcat.txt"; then
      printf '%s\\n' 'Ignored CI-only AppMeasurementService ANR (no GmsCore)' >> "$FLOW"
    else
      cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
      echo 'NSS-owned ANR detected'; return 1
    fi
  fi
}''',
        'third-party measurement ANR filter',
    ),
    (
        '''start_game(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"
  sleep 2
  capture_log "$tag mainmenu"
}''',
        '''start_game(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "$tag-mainmenu"
  local rendered=0 ready_i bytes
  for ready_i in $(seq 1 45); do
    fatal_check || return 1
    adb exec-out screencap -p > "$WORK/render-probe.png" 2>/dev/null || true
    bytes="$(wc -c < "$WORK/render-probe.png" 2>/dev/null || echo 0)"
    if [ "${bytes:-0}" -gt 30000 ]; then
      cp "$WORK/render-probe.png" "$OUT/${tag}-render-ready.png" || true
      rendered=1
      break
    fi
    sleep 1
  done
  [ "$rendered" -eq 1 ] || { cp "$WORK/render-probe.png" "$OUT/${tag}-render-timeout.png" 2>/dev/null || true; echo 'Rendered frame did not become ready'; return 1; }
  test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)"
  capture_log "$tag mainmenu"
}''',
        'render-ready MainMenu bootstrap',
    ),
    (
        '''open_slot0(){
  local tag="$1"
  clear_log; press_career 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 30 "$tag-saveslot"
  shot "$tag-saveslot"
  clear_log; press_slot0 2
}''',
        '''open_slot0(){
  local tag="$1" attempt reached=0
  for attempt in 1 2 3; do
    clear_log
    echo "Career press attempt $attempt/3"
    press_career 2
    if wait_log 'Create Screen:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot' 6 "$tag-saveslot-attempt-$attempt"; then
      reached=1
      break
    fi
    fatal_check || return 1
  done
  [ "$reached" -eq 1 ] || { echo 'SaveSlot not reached after 3 controlled Career presses'; return 1; }
  capture_log "$tag saveslot"
  shot "$tag-saveslot"
  local slot_attempt slot_hit=0
  for slot_attempt in 1 2 3; do
    clear_log
    echo "Slot0 press attempt $slot_attempt/3"
    press_slot0 3
    adb logcat -d -v brief > "$WORK/$tag-slot0-attempt-$slot_attempt.txt" 2>/dev/null || true
    if grep -q 'HitGadget: saveslot.btn_Slot0' "$WORK/$tag-slot0-attempt-$slot_attempt.txt"; then
      slot_hit=1
      break
    fi
    fatal_check || return 1
  done
  [ "$slot_hit" -eq 1 ] || { echo 'Slot0 did not register after 3 controlled presses'; return 1; }
}''',
        'bounded Career and Slot0 input proof',
    ),
    (
        '''sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")"; "$ZIPALIGN" -f 4 "$src" "$tmp"; "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"; "$APKSIGNER" verify --verbose "$dst" >/dev/null; }''',
        '''sign_one(){
  local src="$1" dst="$2" tmp
  tmp="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$tmp"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}''',
        'nounset-safe sign_one',
    ),
    (
        '''press_career(){ press_logical 471 541 "${1:-3}"; }''',
        '''press_career(){
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"
  case "$size" in
    *1080x2280*) adb shell input touchscreen tap 795 1399 </dev/null || true; sleep "${1:-3}" ;;
    *) press_logical 471 541 "${1:-3}" ;;
  esac
}''',
        'Pixel 4 Career target',
    ),
    (
        '''PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/trial-bootstrap-patch.txt"''',
        '''PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/trial-bootstrap-patch.txt"
python3 stage3_tools/patch_first_run_overlays.py "$WORK/base-career-unsigned.apk" "$WORK/base-career-overlay-unsigned.apk" | tee "$OUT/first-run-overlay-patch.txt"
mv "$WORK/base-career-overlay-unsigned.apk" "$WORK/base-career-unsigned.apk"''',
        'proven first-run overlay bypass',
    ),
    (
        '''  clear_log; press_play 4; fatal_check; capture_log "$scenario mutation trigger"
  sleep 2''',
        '''  clear_log; press_play 4
  wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 "$scenario-leaguefixtures"
  fatal_check; capture_log "$scenario GameMenu -> LeagueFixtures"
  clear_log; press_play 4; fatal_check; capture_log "$scenario mutation trigger"
  sleep 2''',
        'LeagueFixtures traversal before PlayMatches trigger',
    ),
]

for old, new, label in replacements:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'expected one source pattern for {label}, found {count}')
    text = text.replace(old, new)

# Stage2 and the previously proven Stage4 source used different default delays
# for this helper. Match either literal variant instead of coupling the preparer
# to one source snapshot.
play_pattern = re.compile(r'press_play\(\)\{ press_logical 553 829 "\$\{1:-(2|3)\}"; \}')
play_matches = list(play_pattern.finditer(text))
if len(play_matches) != 1:
    raise SystemExit(f'expected one Stage2/Stage4 press_play helper, found {len(play_matches)}')
text = play_pattern.sub('''press_play(){
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"
  case "$size" in
    *1080x2280*) adb shell input touchscreen tap 935 1850 </dev/null || true; sleep "${1:-3}" ;;
    *) press_logical 553 829 "${1:-3}" ;;
  esac
}''', text, count=1)

dst.write_text(text, encoding='utf-8')
print(f'Prepared Stage2 gate with proven Pixel4 bootstrap, traversal, and strict NSS failure filtering: {dst}')
