#!/usr/bin/env python3
from pathlib import Path
import sys

PATCH_ANCHOR = '''python3 stage3/patch_stage3_knockout_apk.py "$MODE" "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \\
  --evidence "$OUT/STAGE3_KNOCKOUT_APK_PATCH.json" | tee "$OUT/STAGE3_KNOCKOUT_APK_PATCH.txt"'''
PATCH_REPLACEMENT = '''python3 endurance/patch_long_career_season_probe.py "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \\
  | tee "$OUT/LONG_CAREER_APK_PATCH.txt"'''
TAIL_MARKER = '# Drive normal stock UI to the next playable match.'

TAIL = r'''# Progressive same-Career endurance loop.
SEASON_COUNT="${LONG_CAREER_SEASONS:-8}"
FLOW="$OUT/LONG_CAREER_FLOW.log"
: > "$FLOW"

dump_save(){
  local tag="$1" remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml" xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || true
  grep -q 'monkeystate' "$xml" || { echo "Could not read $remote for $tag"; return 1; }
}

capture_flow(){
  local label="$1"
  {
    echo
    echo "===== $label ====="
    adb logcat -d -v threadtime 2>/dev/null || true
  } >> "$FLOW"
}

open_saved_slot0(){
  local tag="$1" x y
  start_menu
  read -r x y < <(logical_xy 480 664)
  clear_log
  press_physical "$x" "$y" 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 15 "$tag-saveslot"
  shot "$tag-saveslot"
  find_slot0_target "$OUT/$tag-saveslot.png" "$WORK/$tag-slot0.txt"
  read -r SLOT_X SLOT_Y < "$WORK/$tag-slot0.txt"
  clear_log
  press_physical "$SLOT_X" "$SLOT_Y" 3
  wait_log 'LoadCareer saveslot:[[:space:]]*0' 30 "$tag-loadcareer"
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 45 "$tag-gamemenu"
  fatal_check
}

# Baseline is the durable fresh Career created above.
dump_save season-0-baseline
fatal_check

for season in $(seq 1 "$SEASON_COUNT"); do
  echo "===== LONG CAREER SEASON $season/$SEASON_COUNT =====" | tee -a "$FLOW"

  clear_log
  press_play 3
  wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 "season-${season}-leaguefixtures"
  fatal_check

  clear_log
  press_play 3
  wait_log '\bNewSeason\b' 60 "season-${season}-newseason"
  wait_log 'CallFunc:[[:space:]]*NewSeasonSetUp1' 60 "season-${season}-setup1"
  wait_log 'CallFunc:[[:space:]]*NewSeasonSetUp2' 60 "season-${season}-setup2"
  wait_log 'CallFunc:[[:space:]]*NewSeasonSetUp3' 60 "season-${season}-setup3"
  wait_log 'CallFunc:[[:space:]]*NewSeasonSetUp4' 60 "season-${season}-setup4"
  wait_log 'New Season - Save' 60 "season-${season}-final-save"
  wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 "season-${season}-gamemenu"
  fatal_check
  capture_flow "season $season post-rollover"
  dump_save "season-${season}-post"
  shot "season-${season}-post"

  # Mandatory restart + stock LoadCareer after every season.
  open_saved_slot0 "season-${season}-reload"
  dump_save "season-${season}-reload"
  fatal_check
  capture_flow "season $season after restart/load"
  echo "LONG_CAREER_SEASON_${season}_RUNTIME_PASS" | tee -a "$FLOW"
done

python3 endurance/verify_long_career.py "$OUT" "$SEASON_COUNT" | tee "$OUT/LONG_CAREER_ENDURANCE_RESULT.txt"
grep -q 'VERDICT=LONG_CAREER_ENDURANCE_PASS' "$OUT/LONG_CAREER_ENDURANCE_RESULT.txt"
! grep -qiE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$FLOW"
echo 'VERDICT=LONG_CAREER_RUNTIME_PASS'
'''


def transform(text: str) -> str:
    if text.count(PATCH_ANCHOR) != 1:
        raise ValueError(f'expected one Stage3 patch anchor, found {text.count(PATCH_ANCHOR)}')
    text = text.replace(PATCH_ANCHOR, PATCH_REPLACEMENT, 1)
    if text.count(TAIL_MARKER) != 1:
        raise ValueError(f'expected one tail marker, found {text.count(TAIL_MARKER)}')
    prefix = text.split(TAIL_MARKER, 1)[0]
    return prefix + TAIL_MARKER + '\n' + TAIL


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_long_career_driver.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(transform(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched long Career driver: {src} -> {dst}')


if __name__ == '__main__':
    main()
