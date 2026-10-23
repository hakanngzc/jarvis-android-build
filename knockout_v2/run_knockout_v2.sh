#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
case "$MODE" in
  extra-time|shootout) ;;
  *) echo 'usage: bash knockout_v2/run_knockout_v2.sh extra-time|shootout' >&2; exit 2 ;;
esac

RUNTIME="$RUNNER_TEMP/nss_stage3_knockout_runtime_v2.sh"
cp nss_stage3_knockout_runtime.sh "$RUNTIME"

python3 - "$RUNTIME" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
text = p.read_text(encoding='utf-8')

def replace_once(old: str, new: str, label: str) -> None:
    global text
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'{label}: expected exactly one source block, found {count}')
    text = text.replace(old, new, 1)

replace_once(
    '  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"\n',
    '  local src="$1" dst="$2"\n  local aligned="$WORK/aligned-$(basename "$dst")"\n',
    'sign_one declaration',
)

replace_once(
    'press_physical 810 1450 2\n'
    "wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot\n",
    'python3 stage3/pick_mainmenu_play.py "$OUT/stock-mainmenu-rendered.png" "$WORK/mainmenu-play.txt"\n'
    'read -r MAIN_X MAIN_Y < "$WORK/mainmenu-play.txt"\n'
    'press_physical "$MAIN_X" "$MAIN_Y" 2\n'
    "wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot\n",
    'initial mainmenu Play',
)

replace_once(
    'find_slot0_target "$OUT/saveslot.png" "$WORK/slot0.txt"\n',
    'python3 stage3/pick_saveslot.py "$OUT/saveslot.png" "$WORK/slot0.txt"\n',
    'initial saveslot picker',
)

old_career = (
    "wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 35 gamemenu\n"
    'shot career-gamemenu\n'
)
new_career = r'''echo 'Restarting after stock Career save and loading slot 0'
RELOAD_READY=0
for RELOAD_ATTEMPT in 1 2 3; do
  start_menu
  python3 stage3/pick_mainmenu_play.py "$OUT/stock-mainmenu-rendered.png" "$WORK/reload-mainmenu-play.txt"
  read -r RELOAD_MAIN_X RELOAD_MAIN_Y < "$WORK/reload-mainmenu-play.txt"
  clear_log
  press_physical "$RELOAD_MAIN_X" "$RELOAD_MAIN_Y" 3
  shot "reload-saveslot-attempt-$RELOAD_ATTEMPT"
  if python3 stage3/pick_saveslot.py "$OUT/reload-saveslot-attempt-$RELOAD_ATTEMPT.png" "$WORK/reload-slot0.txt"; then
    cp "$OUT/reload-saveslot-attempt-$RELOAD_ATTEMPT.png" "$OUT/reload-saveslot.png"
    RELOAD_READY=1
    break
  fi
  echo "Reload SaveSlot visual retry $RELOAD_ATTEMPT"
done
[ "$RELOAD_READY" -eq 1 ] || { echo 'Unable to render reload SaveSlot after 3 attempts'; exit 204; }
read -r RELOAD_SLOT_X RELOAD_SLOT_Y < "$WORK/reload-slot0.txt"
clear_log
press_physical "$RELOAD_SLOT_X" "$RELOAD_SLOT_Y" 3
adb logcat -d -v brief > "$WORK/reload-slot-progress.txt" 2>/dev/null || true
if ! grep -qiE 'LoadCareer saveslot:[[:space:]]*0|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/reload-slot-progress.txt"; then
  press_message_accept 3
fi
wait_log 'LoadCareer saveslot:[[:space:]]*0|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 30 reload-career
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 30 gamemenu
shot career-gamemenu
'''
replace_once(old_career, new_career, 'career reload block')

old_start = '''clear_log
press_play 2
sleep 1
shot "knockout-$MODE-t1"
'''
new_start = '''# First-use Match tutorial consumes the first tap. Dismiss it in the safe
# commentary-panel area, then locate the real circular PLAY control visually.
press_physical 540 1140 2
shot knockout-match-ready
python3 knockout_v2/pick_match_play.py "$OUT/knockout-match-ready.png" "$WORK/match-play.txt"
read -r MATCH_PLAY_X MATCH_PLAY_Y < "$WORK/match-play.txt"
clear_log
press_physical "$MATCH_PLAY_X" "$MATCH_PLAY_Y" 2
sleep 1
shot "knockout-$MODE-t1"
'''
replace_once(old_start, new_start, 'match PLAY boundary')

old_second = '''if [ "$MODE" = shootout ]; then
  clear_log
  press_play 2
  sleep 1
  shot knockout-shootout-after-second-play-t1
'''
new_second = '''if [ "$MODE" = shootout ]; then
  # Some stock transitions expose PLAY once more before the first penalty.
  # Only press it when the visual fingerprint is actually present.
  if python3 knockout_v2/pick_match_play.py "$OUT/knockout-shootout-t3.png" "$WORK/shootout-play.txt"; then
    read -r SHOOTOUT_PLAY_X SHOOTOUT_PLAY_Y < "$WORK/shootout-play.txt"
    clear_log
    press_physical "$SHOOTOUT_PLAY_X" "$SHOOTOUT_PLAY_Y" 2
  else
    clear_log
  fi
  sleep 1
  shot knockout-shootout-after-second-play-t1
'''
replace_once(old_second, new_second, 'shootout follow-up PLAY')

p.write_text(text, encoding='utf-8')
PY

bash -n "$RUNTIME"
python3 -m unittest knockout_v2/test_pick_match_play.py -v

# The repository contract pins this exact Android Emulator build.
emulator -version 2>&1 | tee "$RUNNER_TEMP/nss-stage3-emulator-version.txt"
grep -q 'build_id 16428233' "$RUNNER_TEMP/nss-stage3-emulator-version.txt"

bash "$RUNTIME" "$MODE"
