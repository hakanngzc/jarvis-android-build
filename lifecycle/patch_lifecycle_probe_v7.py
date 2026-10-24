#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v6 import patch_script as v6_patch_script

RELOAD_HELPER_ANCHOR = r'''reload_saved_career_after_setup(){
  # First-run news/transition screens are irrelevant to lifecycle coverage and
  # proved timing-sensitive. Cross a real persistence boundary instead: force
  # stop after SAVE CAREER, reopen the same stock slot, and require LoadCareer.
  start_menu
  open_saveslot_from_mainmenu lifecycle-reload-saveslot
  local sx sy
  read -r sx sy < <(logical_xy 320 280)
  clear_log
  press_physical "$sx" "$sy" 3
  if ! wait_log 'LoadCareer saveslot:[[:space:]]*0' 8 lifecycle-loadcareer-direct; then
    # Some stock paths show one confirmation/message before loading.
    press_message_accept 2
    wait_log 'LoadCareer saveslot:[[:space:]]*0' 25 lifecycle-loadcareer-confirmed
  fi
  wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 40 lifecycle-reloaded-gamemenu
  lifecycle_record career_reload_from_stock_save PASS
}'''

RELOAD_HELPER_REPLACEMENT = r'''reload_saved_career_after_setup(){
  # Cross the durable stock save boundary, then reopen the saved Career. API34
  # can drop a touch while rendering/ads are busy, so locate the actual SaveSlot
  # card from each fresh screenshot and retry only within a strict budget.
  start_menu
  open_saveslot_from_mainmenu lifecycle-reload-saveslot
  local attempt sx sy png target loaded back_used attempt_log
  loaded=0
  back_used=0
  for attempt in 1 2 3; do
    png="$OUT/lifecycle-reload-slot-attempt-${attempt}.png"
    target="$WORK/lifecycle-reload-slot-attempt-${attempt}.txt"
    adb exec-out screencap -p > "$png" 2>/dev/null || true

    if ! find_slot0_target "$png" "$target" > "$OUT/lifecycle-reload-slot-attempt-${attempt}-fingerprint.txt" 2>&1; then
      adb shell dumpsys activity activities > "$OUT/lifecycle-reload-slot-attempt-${attempt}-activity.txt" 2>/dev/null || true
      adb shell dumpsys window windows > "$OUT/lifecycle-reload-slot-attempt-${attempt}-window.txt" 2>/dev/null || true
      adb shell uiautomator dump /sdcard/lifecycle-reload-slot.xml >/dev/null 2>&1 || true
      adb shell cat /sdcard/lifecycle-reload-slot.xml > "$OUT/lifecycle-reload-slot-attempt-${attempt}-ui.xml" 2>/dev/null || true
      adb logcat -d -v threadtime > "$OUT/lifecycle-reload-slot-attempt-${attempt}-logcat.txt" 2>/dev/null || true

      if [ "$back_used" -ne 0 ]; then
        echo 'reload SaveSlot fingerprint missing after recovery BACK was already used'
        return 1
      fi
      adb shell input keyevent 4 >/dev/null 2>&1 || true
      back_used=1
      sleep 2
      png="$OUT/lifecycle-reload-slot-attempt-${attempt}-post-back.png"
      target="$WORK/lifecycle-reload-slot-attempt-${attempt}-post-back.txt"
      adb exec-out screencap -p > "$png" 2>/dev/null || true
      if ! find_slot0_target "$png" "$target" > "$OUT/lifecycle-reload-slot-attempt-${attempt}-post-back-fingerprint.txt" 2>&1; then
        adb shell dumpsys activity activities > "$OUT/lifecycle-reload-slot-attempt-${attempt}-post-back-activity.txt" 2>/dev/null || true
        adb shell dumpsys window windows > "$OUT/lifecycle-reload-slot-attempt-${attempt}-post-back-window.txt" 2>/dev/null || true
        adb logcat -d -v threadtime > "$OUT/lifecycle-reload-slot-attempt-${attempt}-post-back-logcat.txt" 2>/dev/null || true
        echo 'reload SaveSlot fingerprint still missing after one BACK'
        return 1
      fi
    fi

    read -r sx sy < "$target"
    clear_log
    press_physical "$sx" "$sy" 3
    if wait_log 'LoadCareer saveslot:[[:space:]]*0' 10 "lifecycle-loadcareer-attempt-${attempt}"; then
      loaded=1
      break
    fi

    shot "lifecycle-reload-slot-attempt-${attempt}-miss"
    adb shell dumpsys activity activities > "$OUT/lifecycle-reload-slot-attempt-${attempt}-miss-activity.txt" 2>/dev/null || true
    adb shell dumpsys window windows > "$OUT/lifecycle-reload-slot-attempt-${attempt}-miss-window.txt" 2>/dev/null || true
    adb shell uiautomator dump /sdcard/lifecycle-reload-slot-miss.xml >/dev/null 2>&1 || true
    adb shell cat /sdcard/lifecycle-reload-slot-miss.xml > "$OUT/lifecycle-reload-slot-attempt-${attempt}-miss-ui.xml" 2>/dev/null || true
    attempt_log="$OUT/lifecycle-reload-slot-attempt-${attempt}-miss-logcat.txt"
    adb logcat -d -v threadtime > "$attempt_log" 2>/dev/null || true

    # A genuine stock confirmation/message is allowed one normal accept action;
    # otherwise do not guess at overlay coordinates and simply re-fingerprint.
    if grep -qiE 'SETTING ACTIVE:[[:space:]]*message|SetActive:[[:space:]]*message|Create Screen:[[:space:]]*message' "$attempt_log"; then
      clear_log
      press_message_accept 2
      if wait_log 'LoadCareer saveslot:[[:space:]]*0' 8 "lifecycle-loadcareer-confirmed-attempt-${attempt}"; then
        loaded=1
        break
      fi
    fi
  done

  if [ "$loaded" -ne 1 ]; then
    adb logcat -d -v threadtime > "$OUT/lifecycle-loadcareer-bounded-retries-failed.txt" 2>/dev/null || true
    echo 'Could not LoadCareer after three visually verified SaveSlot attempts'
    return 1
  fi
  wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 40 lifecycle-reloaded-gamemenu
  lifecycle_record career_reload_from_stock_save PASS
}'''


def harden_reload_navigation(text: str) -> str:
    count = text.count(RELOAD_HELPER_ANCHOR)
    if count != 1:
        raise ValueError(f'expected one v6 reload helper block, found {count}')
    return text.replace(RELOAD_HELPER_ANCHOR, RELOAD_HELPER_REPLACEMENT, 1)


def patch_script(text: str) -> str:
    generated = v6_patch_script(text)
    return harden_reload_navigation(generated)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v7.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v7: {src} -> {dst}')


if __name__ == '__main__':
    main()
