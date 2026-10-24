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
POST_CREATE_ANCHOR = '''for _ in 1 2 3 4 5; do
  press_message_accept 2
  fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/save-progress.txt"; then break; fi
done
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 35 gamemenu'''
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
wait_for_initial_career_save(){
  local attempt
  for attempt in 1 2 3 4 5; do
    adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
    if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/save-progress.txt"; then
      lifecycle_record initial_career_save PASS
      return 0
    fi
    press_message_accept 2
    fatal_check || return 1
  done
  adb logcat -d -v threadtime > "$OUT/initial-career-save-timeout.log" 2>/dev/null || true
  echo 'Initial Career did not reach a stock save boundary'
  return 1
}
reload_saved_career_after_setup(){
  # First-run news/transition screens are irrelevant to lifecycle coverage and
  # proved timing-sensitive. Cross a real persistence boundary instead: force
  # stop after SAVE CAREER, reopen the same stock slot, and require LoadCareer.
  start_menu
  clear_log
  press_physical 810 1450 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 lifecycle-reload-saveslot
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
    text = one_replace(text, SIGN_ANCHOR,
        '  local src="$1" dst="$2"\n  local aligned="$WORK/aligned-$(basename "$dst")"', 'sign_one')
    text = one_replace(text, HELPER_ANCHOR, HELPER, 'helper')
    text = one_replace(text, MAIN_ANCHOR,
        'start_menu\nlifecycle_warm_relaunch mainmenu\nstart_menu\nadb shell wm size > "$OUT/wm-size.txt"', 'mainmenu')
    text = one_replace(text, SLOT_ANCHOR,
        'shot saveslot\nread -r SLOT_X SLOT_Y < <(logical_xy 320 280)\nclear_log\npress_physical "$SLOT_X" "$SLOT_Y" 3', 'slot1')
    text = one_replace(text, POST_CREATE_ANCHOR,
        'wait_for_initial_career_save\nreload_saved_career_after_setup', 'post-create reload')
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
