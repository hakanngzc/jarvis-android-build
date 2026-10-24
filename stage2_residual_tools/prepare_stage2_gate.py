#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
text = src.read_text(encoding='utf-8')

replacements = [
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
        '''press_play(){ press_logical 553 829 "${1:-3}"; }''',
        '''press_play(){
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"
  case "$size" in
    *1080x2280*) adb shell input touchscreen tap 935 1850 </dev/null || true; sleep "${1:-3}" ;;
    *) press_logical 553 829 "${1:-3}" ;;
  esac
}''',
        'Pixel 4 Play target',
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
        '''  # Proven Stage4 traversal: GameMenu -> LeagueFixtures -> PlayMatches.
  clear_log; press_play 4
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

dst.write_text(text, encoding='utf-8')
print(f'Prepared Stage2 gate with proven Pixel 4 targets and Stage4 traversal: {dst}')
