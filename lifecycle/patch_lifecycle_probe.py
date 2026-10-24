#!/usr/bin/env python3
import sys
from pathlib import Path

SIGN_ANCHOR = '  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"'
HELPER_ANCHOR = 'clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }\n\nstart_menu(){'
MAIN_ANCHOR = 'start_menu\nadb shell wm size > "$OUT/wm-size.txt"'
SLOT_ANCHOR = '''shot saveslot
find_slot0_target "$OUT/saveslot.png" "$WORK/slot0.txt"
read -r SLOT_X SLOT_Y < "$WORK/slot0.txt"
clear_log
press_physical "$SLOT_X" "$SLOT_Y" 3'''
CAREER_ANCHOR = 'shot career-gamemenu\n\n# Drive normal stock UI to the next playable match.'
MATCH_ANCHOR = 'press_play 2\nsleep 1\nshot "knockout-$MODE-t1"'

HELPER = r'''clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }

pid_one(){ adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' | awk '{print $1}'; }
assert_foreground(){
  adb shell dumpsys activity activities > "$WORK/lifecycle-activity.txt" 2>/dev/null || true
  grep -qE 'ResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|mResumedActivity.*com\.newstargames\.newstarsoccer.*MonkeyGame|topResumedActivity=.*com\.newstargames\.newstarsoccer.*MonkeyGame' "$WORK/lifecycle-activity.txt"
}
lifecycle_record(){
  printf '%s=%s\n' "$1" "$2" | tee -a "$OUT/LIFECYCLE_RUNTIME_RESULT.txt"
}
lifecycle_warm_relaunch(){
  local tag="$1" before after
  before="$(pid_one)"; [ -n "$before" ] || { echo "missing PID before warm relaunch ($tag)"; return 1; }
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  sleep 2
  after="$(pid_one)"; [ "$before" = "$after" ] || { echo "process changed during warm relaunch ($tag): $before -> $after"; return 1; }
  assert_foreground || { echo "app not foreground after warm relaunch ($tag)"; return 1; }
  fatal_check || return 1
  shot "lifecycle-${tag}-warm"
  lifecycle_record "${tag}_warm_relaunch_same_pid" PASS
}
lifecycle_background_roundtrip(){
  local tag="$1" before hidden after
  before="$(pid_one)"; [ -n "$before" ] || { echo "missing PID before background ($tag)"; return 1; }
  adb shell input keyevent 3 >/dev/null 2>&1 || true
  sleep 3
  hidden="$(pid_one)"; [ "$before" = "$hidden" ] || { echo "process died in background ($tag): $before -> $hidden"; return 1; }
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  sleep 3
  after="$(pid_one)"; [ "$before" = "$after" ] || { echo "process changed after foreground ($tag): $before -> $after"; return 1; }
  assert_foreground || { echo "app not foreground after background roundtrip ($tag)"; return 1; }
  fatal_check || return 1
  shot "lifecycle-${tag}-resumed"
  lifecycle_record "${tag}_background_foreground_same_pid" PASS
}
: > "$OUT/LIFECYCLE_RUNTIME_RESULT.txt"
lifecycle_record api_level "${LIFECYCLE_API:-unknown}"

start_menu(){'''

def one_replace(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise ValueError(f'expected one {label} anchor, found {count}')
    return text.replace(old, new, 1)

def patch_script(text: str) -> str:
    # The inherited Stage3 driver had a latent `set -u` bug: `$dst` was
    # expanded inside the same `local` command that assigned it. Split the
    # assignments so lifecycle failures cannot be polluted by signing noise.
    text = one_replace(text, SIGN_ANCHOR,
        '  local src="$1" dst="$2"\n  local aligned="$WORK/aligned-$(basename "$dst")"', 'sign_one')
    text = one_replace(text, HELPER_ANCHOR, HELPER, 'helper')
    # Warm relaunch is a standalone assertion. Restart the stable stock menu
    # afterward so any Activity focus/onNewIntent side effect cannot influence
    # the Career navigation that follows.
    text = one_replace(text, MAIN_ANCHOR,
        'start_menu\nlifecycle_warm_relaunch mainmenu\nstart_menu\nadb shell wm size > "$OUT/wm-size.txt"', 'mainmenu')
    # The old image-band heuristic selected the Tutorial footer on a fresh
    # SaveSlot page. Slot 1 / New Career is stable in the game's 640x960 logical
    # coordinate system, so use the existing logical->physical scaler instead.
    text = one_replace(text, SLOT_ANCHOR,
        'shot saveslot\nread -r SLOT_X SLOT_Y < <(logical_xy 320 280)\nclear_log\npress_physical "$SLOT_X" "$SLOT_Y" 3', 'slot1')
    text = one_replace(text, CAREER_ANCHOR,
        'shot career-gamemenu\nlifecycle_background_roundtrip career\n\n# Drive normal stock UI to the next playable match.', 'career')
    text = one_replace(text, MATCH_ANCHOR,
        'press_play 2\nsleep 1\nshot "knockout-$MODE-t1"\nlifecycle_background_roundtrip match', 'match')
    return text

def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe: {src} -> {dst}')

if __name__ == '__main__': main()
