#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v2 import patch_script as v2_patch_script

HELPER_ANCHOR = 'reload_saved_career_after_setup(){'
HELPER = r'''foreground_from_recents(){
  local tag="$1" size w h x y
  adb shell input keyevent 187 >/dev/null 2>&1 || true
  sleep 2
  shot "lifecycle-${tag}-recents"
  size="$(adb shell wm size 2>/dev/null | tr -d '\r' | grep -Eo '[0-9]+x[0-9]+' | tail -1 || true)"
  [ -n "$size" ] || { echo "could not read display size for Recents ($tag)"; return 1; }
  w="${size%x*}"; h="${size#*x}"; x=$((w/2)); y=$((h/2))
  adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
  sleep 4
  adb shell dumpsys activity activities > "$OUT/lifecycle-${tag}-recents-activity.txt" 2>/dev/null || true
  if ! grep -qE 'ResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|mResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|topResumedActivity=.*com\.newstargames\.newstarsoccer.*MonkeyGame' "$OUT/lifecycle-${tag}-recents-activity.txt"; then
    shot "lifecycle-${tag}-recents-not-foreground"
    adb logcat -d -v threadtime > "$OUT/lifecycle-${tag}-recents-not-foreground-logcat.txt" 2>/dev/null || true
    lifecycle_record "${tag}_recents_foreground" FAIL
    echo "NSS not foreground after Recents ($tag)"
    return 1
  fi
  lifecycle_record "${tag}_recents_foreground" PASS
}

open_saveslot_from_mainmenu(){
  local tag="$1" attempt x y
  read -r x y < <(logical_xy 480 664)
  for attempt in 1 2 3; do
    clear_log
    press_physical "$x" "$y" 2
    if wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 6 "${tag}-attempt-${attempt}"; then
      echo "Opened SaveSlot via logical Career target on attempt $attempt"
      return 0
    fi
    shot "${tag}-attempt-${attempt}-miss"
    start_menu
  done
  adb logcat -d -v threadtime > "$OUT/${tag}-open-saveslot-failed.log" 2>/dev/null || true
  echo "Could not open SaveSlot from MainMenu ($tag)"
  return 1
}

reload_saved_career_after_setup(){'''

ROUNDTRIP_ANCHOR = '''  lifecycle_record "${tag}_background_process_survived" PASS
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  sleep 3
  after="$(pid_one)"'''
ROUNDTRIP_REPLACEMENT = '''  lifecycle_record "${tag}_background_process_survived" PASS
  foreground_from_recents "$tag" || return 1
  after="$(pid_one)"'''

INITIAL_SAVE_ANCHOR = '''clear_log
press_physical 810 1450 2
wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot'''
INITIAL_SAVE_REPLACEMENT = '''open_saveslot_from_mainmenu saveslot'''

RELOAD_SAVE_ANCHOR = '''  clear_log
  press_physical 810 1450 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 lifecycle-reload-saveslot'''
RELOAD_SAVE_REPLACEMENT = '''  open_saveslot_from_mainmenu lifecycle-reload-saveslot'''


def one_replace(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'expected one {label} anchor, found {count}')
    return text.replace(old, new, 1)


def harden_generated_script(text: str) -> str:
    text = one_replace(text, HELPER_ANCHOR, HELPER, 'v3 helper')
    text = one_replace(text, ROUNDTRIP_ANCHOR, ROUNDTRIP_REPLACEMENT, 'Recents roundtrip')
    text = one_replace(text, INITIAL_SAVE_ANCHOR, INITIAL_SAVE_REPLACEMENT, 'initial Career entry')
    text = one_replace(text, RELOAD_SAVE_ANCHOR, RELOAD_SAVE_REPLACEMENT, 'reload Career entry')
    return text


def patch_script(text: str) -> str:
    return harden_generated_script(v2_patch_script(text))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v3.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v3: {src} -> {dst}')


if __name__ == '__main__':
    main()
