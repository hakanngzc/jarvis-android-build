#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'expected one source pattern for {label}, found {count}')
    return text.replace(old, new, 1)


def replace_regex(text: str, pattern: str, replacement: str, label: str) -> str:
    rx = re.compile(pattern, re.S)
    matches = list(rx.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one source pattern for {label}, found {len(matches)}')
    return rx.sub(lambda _: replacement, text, count=1)


def prepare_text(text: str) -> str:
    sign_old = '''sign_one(){ local src="$1" dst="$2" tmp="$WORK/aligned-$(basename "$dst")"; "$ZIPALIGN" -f 4 "$src" "$tmp"; "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"; "$APKSIGNER" verify --verbose "$dst" >/dev/null; }'''
    sign_new = '''sign_one(){
  local src="$1" dst="$2" tmp
  tmp="$WORK/aligned-$(basename "$dst")"
  "$ZIPALIGN" -f 4 "$src" "$tmp"
  "$APKSIGNER" sign --ks "$WORK/ci.keystore" --ks-key-alias ci --ks-pass pass:android --key-pass pass:android --out "$dst" "$tmp"
  "$APKSIGNER" verify --verbose "$dst" >/dev/null
}'''
    text = replace_exact(text, sign_old, sign_new, 'nounset-safe sign_one')

    # Stage2 has a multi-line dump_save helper that needs nounset hardening.
    # Stage4-natural intentionally uses a different one-line helper, so do not
    # force a Stage2-specific source shape onto it.
    dump_old = '''dump_save(){
  local tag="$1" xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$REMOTE_PREF" > "$xml"
  grep -q 'monkeystate' "$xml"
}'''
    dump_new = '''dump_save(){
  local tag="$1" xml
  xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$REMOTE_PREF" > "$xml"
  grep -q 'monkeystate' "$xml"
}'''
    if dump_old in text:
        text = replace_exact(text, dump_old, dump_new, 'nounset-safe dump_save')

    # build_probe exists only in the Stage2 residual mutation gate. Stage4 has
    # no probe APK builder because the season run must remain natural.
    build_old = '''build_probe(){
  local scenario="$1" dest="${2:-}" out="$WORK/base-$scenario-unsigned.apk"
  args=(stage2_residual_tools/patch_stage2_residual_probe.py "$WORK/base-career-unsigned.apk" "$out" --scenario "$scenario")'''
    build_new = '''build_probe(){
  local scenario="$1" dest="${2:-}" out
  out="$WORK/base-$scenario-unsigned.apk"
  args=(stage2_residual_tools/patch_stage2_residual_probe.py "$WORK/base-career-unsigned.apk" "$out" --scenario "$scenario")'''
    if build_old in text:
        text = replace_exact(text, build_old, build_new, 'nounset-safe build_probe')

    career_old = '''press_career(){ press_logical 471 541 "${1:-3}"; }'''
    career_new = '''press_career(){
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"
  case "$size" in
    *1080x2280*)
      echo 'Career target (proven stock API29 Pixel 4): 795,1399'
      adb shell input touchscreen tap 795 1399 </dev/null || true
      sleep "${1:-3}"
      ;;
    *) press_logical 471 541 "${1:-3}" ;;
  esac
}'''
    text = replace_exact(text, career_old, career_new, 'Pixel 4 Career target')

    play_pattern = r'''press_play\(\)\{ press_logical 553 829 "\$\{1:-(2|3)\}"; \}'''
    play_matches = list(re.finditer(play_pattern, text))
    if len(play_matches) != 1:
        raise SystemExit(f'expected one Stage2/Stage4 press_play helper, found {len(play_matches)}')
    play_delay = play_matches[0].group(1)
    play_new = f'''press_play(){{
  local size
  size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"
  case "$size" in
    *1080x2280*)
      echo 'Play target (proven stock API29 Pixel 4): 935,1850'
      adb shell input touchscreen tap 935 1850 </dev/null || true
      sleep "${{1:-{play_delay}}}"
      ;;
    *) press_logical 553 829 "${{1:-{play_delay}}}" ;;
  esac
}}'''
    text = re.sub(play_pattern, lambda _: play_new, text, count=1)

    fatal_new = '''fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true

  local anr_count measurement_anr_count
  anr_count="$(grep -c 'ANR in com\\.newstargames\\.newstarsoccer' "$WORK/live-logcat.txt" 2>/dev/null || true)"
  measurement_anr_count="$(grep -c 'Reason: executing service com.newstargames.newstarsoccer/com.google.android.gms.measurement.AppMeasurementService' "$WORK/live-logcat.txt" 2>/dev/null || true)"
  if [ "${anr_count:-0}" -gt 0 ]; then
    if [ "$anr_count" -eq "$measurement_anr_count" ]; then
      cp "$WORK/live-logcat.txt" "$OUT/ignored-gms-measurement-anr.txt" 2>/dev/null || true
    else
      cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" 2>/dev/null || true
      echo 'NSS-owned ANR detected'
      return 1
    fi
  fi

  if grep -qiE 'Process: com\\.newstargames\\.newstarsoccer, PID:|FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" 2>/dev/null || true
    echo 'NSS-owned crash detected'
    return 1
  fi
}'''
    text = replace_regex(
        text,
        r'''fatal_check\(\)\{.*?\n\}\s*wait_log\(\)\{''',
        fatal_new + '\nwait_log(){',
        'strict fatal_check classifier',
    )

    start_new = '''start_game(){
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
      cp "$WORK/render-probe.png" "$OUT/${tag}-render-ready.png" 2>/dev/null || true
      echo "Rendered frame ready after ${ready_i}s (${bytes} bytes)"
      rendered=1
      break
    fi
    sleep 1
  done
  [ "$rendered" -eq 1 ] || {
    cp "$WORK/render-probe.png" "$OUT/${tag}-render-timeout.png" 2>/dev/null || true
    echo 'Rendered frame did not become ready'
    return 1
  }
  test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)"
  capture_log "$tag mainmenu"
}'''
    text = replace_regex(
        text,
        r'''start_game\(\)\{.*?\n\}\s*open_slot0\(\)\{''',
        start_new + '\nopen_slot0(){',
        'render-ready MainMenu bootstrap',
    )

    slot_new = '''open_slot0(){
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
    echo "Career press attempt $attempt did not reach SaveSlot; retrying"
  done
  [ "$reached" -eq 1 ] || {
    echo 'SaveSlot not reached after 3 controlled Career presses'
    return 1
  }
  shot "$tag-saveslot"
  capture_log "$tag saveslot"

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
    echo "Slot0 press attempt $slot_attempt did not register; retrying"
  done
  [ "$slot_hit" -eq 1 ] || {
    echo 'Slot0 did not register after 3 controlled presses'
    return 1
  }
}'''
    text = replace_regex(
        text,
        r'''open_slot0\(\)\{.*?\n\}\s*load_existing\(\)\{''',
        slot_new + '\nload_existing(){',
        'bounded Career and Slot0 input proof',
    )

    if 'patch_first_run_overlays.py' not in text:
        trial_line = '''PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_trial_skip_for_persistence_test.py "$BASE" "$WORK/base-career-unsigned.apk" | tee "$OUT/trial-bootstrap-patch.txt"'''
        trial_with_overlay = trial_line + '''
python3 stage3_tools/patch_first_run_overlays.py "$WORK/base-career-unsigned.apk" "$WORK/base-career-overlay-unsigned.apk" | tee "$OUT/first-run-overlay-patch.txt"
mv "$WORK/base-career-overlay-unsigned.apk" "$WORK/base-career-unsigned.apk"'''
        text = replace_exact(text, trial_line, trial_with_overlay, 'proven first-run overlay bypass')

    fresh_gamemenu_wait = '''wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 50 fresh-gamemenu'''
    if fresh_gamemenu_wait in text:
        settle = '''settle_bootstrap_to_gamemenu(){
  local step state_line state
  for step in $(seq 1 30); do
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/bootstrap-settle.txt" 2>/dev/null || true
    state_line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/bootstrap-settle.txt" | tail -1 || true)"
    state="${state_line,,}"
    case "$state" in
      *gamemenu*) return 0 ;;
      *webpage*|*startransition*|*message*)
        clear_log
        press_message_accept 2
        ;;
      *choosenation*|*chooseclub*)
        clear_log
        press_footer_ok 2
        ;;
      *)
        clear_log
        press_message_accept 2
        ;;
    esac
    sleep 1
  done
  cp "$WORK/bootstrap-settle.txt" "$OUT/bootstrap-settle-timeout.txt" 2>/dev/null || true
  echo 'Bootstrap did not settle to GameMenu'
  return 1
}
settle_bootstrap_to_gamemenu
wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 10 fresh-gamemenu
capture_log 'fresh Career post-save -> GameMenu' '''
        text = replace_exact(text, fresh_gamemenu_wait, settle, 'post-save bootstrap settlement')

    traversal_old = '''  clear_log; press_play 4; fatal_check; capture_log "$scenario mutation trigger"
  sleep 2'''
    if traversal_old in text:
        traversal_new = '''  clear_log; press_play 4
  wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 "$scenario-leaguefixtures"
  fatal_check; capture_log "$scenario GameMenu -> LeagueFixtures"
  clear_log; press_play 4; fatal_check; capture_log "$scenario mutation trigger"
  sleep 2'''
        text = replace_exact(text, traversal_old, traversal_new, 'LeagueFixtures traversal before PlayMatches trigger')

    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage2_gate.py INPUT_GATE OUTPUT_GATE')
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2])
    dst.write_text(prepare_text(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Prepared nounset-safe, rendered-frame-gated Pixel4 runtime gate: {dst}')


if __name__ == '__main__':
    main()
