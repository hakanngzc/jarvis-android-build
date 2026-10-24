#!/usr/bin/env python3
from pathlib import Path
import sys

PATCH_ANCHOR = '''python3 stage3/patch_stage3_knockout_apk.py "$MODE" "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \\
  --evidence "$OUT/STAGE3_KNOCKOUT_APK_PATCH.json" | tee "$OUT/STAGE3_KNOCKOUT_APK_PATCH.txt"'''
PATCH_REPLACEMENT = '''python3 endurance/patch_long_career_season_probe.py "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \\
  | tee "$OUT/LONG_CAREER_APK_PATCH.txt"'''
TAIL_MARKER = '# Drive normal stock UI to the next playable match.'
SIGN_ANCHOR = '  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"'
SIGN_REPLACEMENT = '  local src="$1" dst="$2"\n  local aligned="$WORK/aligned-$(basename "$dst")"'
PLAY_EDGE_ANCHOR = 'press_play(){ local x y; read -r x y < <(logical_xy 553 829); press_physical "$x" "$y" "${1:-2}"; }'
PLAY_CENTER_REPLACEMENT = 'press_play(){ local x y; read -r x y < <(logical_xy 553 900); press_physical "$x" "$y" "${1:-2}"; }'
CAREER_OPEN_ANCHOR = '''clear_log
press_physical 810 1450 2
wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot'''
CAREER_OPEN_REPLACEMENT = '''clear_log
read -r CAREER_X CAREER_Y < <(logical_xy 480 624)
press_physical "$CAREER_X" "$CAREER_Y" 2
wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot'''
SLOT_ANCHOR = '''shot saveslot
find_slot0_target "$OUT/saveslot.png" "$WORK/slot0.txt"
read -r SLOT_X SLOT_Y < "$WORK/slot0.txt"
clear_log
press_physical "$SLOT_X" "$SLOT_Y" 3'''
SLOT_REPLACEMENT = '''shot saveslot
read -r SLOT_X SLOT_Y < <(logical_xy 320 280)
clear_log
press_physical "$SLOT_X" "$SLOT_Y" 3'''
POST_CREATE_ANCHOR = '''for _ in 1 2 3 4 5; do
  press_message_accept 2
  fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/save-progress.txt"; then break; fi
done
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 35 gamemenu'''
POST_CREATE_REPLACEMENT = '''for _ in 1 2 3 4 5; do
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/save-progress.txt"; then break; fi
  press_message_accept 2
  fatal_check
done
grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/save-progress.txt" || { echo 'Initial Career did not reach save boundary'; exit 1; }
start_menu
read -r REOPEN_X REOPEN_Y < <(logical_xy 480 624)
REOPENED=0
for reopen_attempt in 1 2 3; do
  clear_log
  press_physical "$REOPEN_X" "$REOPEN_Y" 2
  if wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 6 "endurance-reload-saveslot-attempt-${reopen_attempt}"; then
    REOPENED=1
    break
  fi
  shot "endurance-reload-saveslot-attempt-${reopen_attempt}-miss"
  start_menu
done
[ "$REOPENED" -eq 1 ] || { echo 'Could not reopen SaveSlot after initial Career save'; exit 1; }
read -r RELOAD_X RELOAD_Y < <(logical_xy 320 280)
clear_log
press_physical "$RELOAD_X" "$RELOAD_Y" 3
if ! wait_log 'LoadCareer saveslot:[[:space:]]*0' 8 endurance-loadcareer-direct; then
  press_message_accept 2
  wait_log 'LoadCareer saveslot:[[:space:]]*0' 25 endurance-loadcareer-confirmed
fi
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 40 endurance-reloaded-gamemenu'''
FATAL_ANCHOR = r'''fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qE 'ANR in com\.newstargames\.newstarsoccer|Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
}'''
FATAL_REPLACEMENT = r'''fatal_check(){
  adb logcat -d -v threadtime > "$WORK/live-logcat.txt" 2>/dev/null || true
  if grep -qE 'Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt"; then
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
  local anr_count measurement_count
  anr_count="$(grep -cE 'ANR in com\.newstargames\.newstarsoccer' "$WORK/live-logcat.txt" || true)"
  measurement_count="$(grep -cE 'Reason: executing service com\.newstargames\.newstarsoccer/com\.google\.android\.gms\.measurement\.AppMeasurementService' "$WORK/live-logcat.txt" || true)"
  if [ "$anr_count" -gt 0 ]; then
    if [ "$anr_count" -eq "$measurement_count" ]; then
      cp "$WORK/live-logcat.txt" "$OUT/runtime-ignored-appmeasurement-anr.txt" || true
      echo 'Ignoring AppMeasurementService-only emulator ANR'
      return 0
    fi
    cp "$WORK/live-logcat.txt" "$OUT/runtime-fatal-logcat.txt" || true
    echo 'NSS-owned crash/ANR detected'
    return 1
  fi
}'''

TAIL = r'''# Progressive same-Career endurance loop.
SEASON_COUNT="${LONG_CAREER_SEASONS:-8}"
FLOW="$OUT/LONG_CAREER_FLOW.log"
: > "$FLOW"

flow_fatal_check(){
  if grep -qiE 'Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$FLOW"; then
    echo 'NSS-owned crash recorded in endurance flow'
    return 1
  fi
  local flow_anr_count flow_measurement_count
  flow_anr_count="$(grep -ciE 'ANR in com\.newstargames\.newstarsoccer' "$FLOW" || true)"
  flow_measurement_count="$(grep -ciE 'Reason: executing service com\.newstargames\.newstarsoccer/com\.google\.android\.gms\.measurement\.AppMeasurementService' "$FLOW" || true)"
  if [ "$flow_anr_count" -ne "$flow_measurement_count" ]; then
    echo "Unexpected NSS ANR in endurance flow: anr=$flow_anr_count measurement=$flow_measurement_count"
    return 1
  fi
  [ "$flow_anr_count" -eq "$flow_measurement_count" ]
}

prepare_save_access(){
  adb root > "$OUT/endurance-adb-root.txt" 2>&1 || true
  adb wait-for-device
  adb shell id > "$OUT/endurance-adb-id.txt" 2>&1 || true
  grep -q 'uid=0(root)' "$OUT/endurance-adb-id.txt" || {
    echo 'Endurance save capture requires root adbd on this emulator'
    return 1
  }
}

dump_save(){
  local tag="$1"
  local remote="/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  local xml="$OUT/${tag}-MonkeyGame.xml"
  adb shell cat "$remote" > "$xml" 2>/dev/null || true
  grep -q 'monkeystate' "$xml" || {
    adb shell ls -la "/data/data/$PKG/shared_prefs" > "$OUT/${tag}-shared-prefs-ls.txt" 2>&1 || true
    adb shell pidof "$PKG" > "$OUT/${tag}-pid.txt" 2>/dev/null || true
    echo "Could not read $remote for $tag"
    return 1
  }
}

capture_flow(){
  local label="$1"
  {
    echo
    echo "===== $label ====="
    adb logcat -d -v threadtime 2>/dev/null || true
  } >> "$FLOW"
}

last_active_screen(){
  local line
  adb logcat -d -v brief > "$WORK/endurance-last-active.txt" 2>/dev/null || true
  line="$(grep -Ei 'SETTING ACTIVE:|SetActive:' "$WORK/endurance-last-active.txt" | tail -1 || true)"
  case "${line,,}" in
    *startransition*) echo startransition ;;
    *gamemenu*) echo gamemenu ;;
    *) echo other ;;
  esac
}

settle_loaded_gamemenu(){
  local tag="$1" i screen
  local stable=0
  for i in $(seq 1 30); do
    fatal_check || return 1
    screen="$(last_active_screen)"
    if [ "$screen" = gamemenu ]; then
      stable=$((stable+1))
    else
      stable=0
    fi
    if [ "$stable" -ge 2 ]; then
      echo "Stable GameMenu after load ($tag)"
      return 0
    fi
    sleep 2
  done
  adb logcat -d -v threadtime > "$OUT/${tag}-unstable-gamemenu.log" 2>/dev/null || true
  echo "GameMenu did not stabilize after load ($tag)"
  return 1
}

dismiss_measurement_anr_modal(){
  local tag="$1" attempt xml target live x y anr_count measurement_count
  xml="$OUT/${tag}-measurement-anr-ui.xml"
  target="$WORK/${tag}-measurement-anr-wait-target.txt"
  live="$OUT/${tag}-measurement-anr-live.log"
  rm -f "$target"
  for attempt in $(seq 1 90); do
    adb logcat -d -v threadtime > "$live" 2>/dev/null || true
    if ! grep -qE 'Process: com\.newstargames\.newstarsoccer, PID:|FATAL EXCEPTION.*com\.newstargames\.newstarsoccer' "$live"; then
      anr_count="$(grep -cE 'ANR in com\.newstargames\.newstarsoccer' "$live" || true)"
      measurement_count="$(grep -cE 'Reason: executing service com\.newstargames\.newstarsoccer/com\.google\.android\.gms\.measurement\.AppMeasurementService' "$live" || true)"
      if [ "$anr_count" -gt 0 ] && [ "$anr_count" -eq "$measurement_count" ]; then
        adb shell uiautomator dump /sdcard/endurance-anr.xml >/dev/null 2>&1 || true
        adb shell cat /sdcard/endurance-anr.xml > "$xml" 2>/dev/null || true
        if grep -q 'text="Wait"' "$xml" && grep -qiE 'NSS[^<]*(isn.t|is not)[^<]*responding|NSS[^<]*responding' "$xml"; then
          python3 - "$xml" "$target" <<'PY'
import re,sys,xml.etree.ElementTree as ET
from pathlib import Path
src,dst=sys.argv[1:]
try:
    root=ET.parse(src).getroot()
except Exception:
    raise SystemExit(1)
for node in root.iter('node'):
    if node.attrib.get('text') != 'Wait':
        continue
    m=re.fullmatch(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]',node.attrib.get('bounds',''))
    if not m:
        continue
    x1,y1,x2,y2=map(int,m.groups())
    if x2>x1 and y2>y1:
        Path(dst).write_text(f'{(x1+x2)//2} {(y1+y2)//2}\n',encoding='utf-8')
        raise SystemExit(0)
raise SystemExit(1)
PY
          if [ -s "$target" ]; then
            read -r x y < "$target"
            adb shell input tap "$x" "$y" >/dev/null 2>&1 || true
            printf 'measurement_anr_wait_dismissed=PASS\n' | tee "$OUT/${tag}-measurement-anr-recovery.txt"
            return 0
          fi
        fi
      fi
    fi
    sleep 1
  done
  return 0
}

restart_saved_career(){
  local tag="$1"
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  rm -f "$OUT/${tag}-measurement-anr-recovery.txt" "$OUT/${tag}-measurement-anr-live.log"
  dismiss_measurement_anr_modal "$tag" &
  ENDURANCE_ANR_WATCHER_PID=$!
  if ! wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 "$tag-loadcareer"; then
    kill "$ENDURANCE_ANR_WATCHER_PID" >/dev/null 2>&1 || true
    wait "$ENDURANCE_ANR_WATCHER_PID" 2>/dev/null || true
    return 1
  fi
  if ! wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 "$tag-gamemenu"; then
    kill "$ENDURANCE_ANR_WATCHER_PID" >/dev/null 2>&1 || true
    wait "$ENDURANCE_ANR_WATCHER_PID" 2>/dev/null || true
    return 1
  fi
  if ! settle_loaded_gamemenu "$tag"; then
    kill "$ENDURANCE_ANR_WATCHER_PID" >/dev/null 2>&1 || true
    wait "$ENDURANCE_ANR_WATCHER_PID" 2>/dev/null || true
    return 1
  fi
  kill "$ENDURANCE_ANR_WATCHER_PID" >/dev/null 2>&1 || true
  wait "$ENDURANCE_ANR_WATCHER_PID" 2>/dev/null || true
  fatal_check
}

capture_season_entry_diagnostics(){
  local season="$1" attempt="$2" prefix
  prefix="$OUT/season-${season}-leaguefixtures-attempt-${attempt}"
  shot "season-${season}-leaguefixtures-attempt-${attempt}-before"
  adb shell dumpsys activity activities > "${prefix}-activity.txt" 2>/dev/null || true
  adb shell dumpsys window windows > "${prefix}-window.txt" 2>/dev/null || true
  adb shell pidof "$PKG" > "${prefix}-pid.txt" 2>/dev/null || true
  adb logcat -d -v threadtime > "${prefix}-before-logcat.txt" 2>/dev/null || true
  adb shell uiautomator dump /sdcard/endurance-entry.xml >/dev/null 2>&1 || true
  adb shell cat /sdcard/endurance-entry.xml > "${prefix}-ui.xml" 2>/dev/null || true
  printf 'last_active=%s\n' "$(last_active_screen)" > "${prefix}-state.txt"
}

enter_leaguefixtures(){
  local season="$1" attempt
  for attempt in 1 2 3; do
    capture_season_entry_diagnostics "$season" "$attempt"
    clear_log
    press_play 3
    if wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 10 "season-${season}-leaguefixtures-attempt-${attempt}"; then
      echo "Season $season entered LeagueFixtures on attempt $attempt"
      return 0
    fi
    shot "season-${season}-leaguefixtures-attempt-${attempt}-miss"
    fatal_check || return 1
  done
  adb logcat -d -v threadtime > "$OUT/season-${season}-leaguefixtures-failed.log" 2>/dev/null || true
  echo "Season $season could not enter LeagueFixtures after bounded retries"
  return 1
}

# Baseline is the durable fresh Career created above.
prepare_save_access
dump_save season-0-baseline
fatal_check

for season in $(seq 1 "$SEASON_COUNT"); do
  echo "===== LONG CAREER SEASON $season/$SEASON_COUNT =====" | tee -a "$FLOW"

  enter_leaguefixtures "$season"
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

  restart_saved_career "season-${season}-reload"
  dump_save "season-${season}-reload"
  fatal_check
  capture_flow "season $season after restart/load"
  echo "LONG_CAREER_SEASON_${season}_RUNTIME_PASS" | tee -a "$FLOW"
done

python3 endurance/verify_long_career.py "$OUT" "$SEASON_COUNT" | tee "$OUT/LONG_CAREER_ENDURANCE_RESULT.txt"
grep -q 'VERDICT=LONG_CAREER_ENDURANCE_PASS' "$OUT/LONG_CAREER_ENDURANCE_RESULT.txt"
flow_fatal_check
echo 'VERDICT=LONG_CAREER_RUNTIME_PASS'
'''


def one_replace(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'expected one {label} anchor, found {count}')
    return text.replace(old, new, 1)


def transform(text: str) -> str:
    text = one_replace(text, PATCH_ANCHOR, PATCH_REPLACEMENT, 'Stage3 patch')
    text = one_replace(text, PLAY_EDGE_ANCHOR, PLAY_CENTER_REPLACEMENT, 'Play hitbox')
    text = one_replace(text, SIGN_ANCHOR, SIGN_REPLACEMENT, 'sign_one')
    text = one_replace(text, CAREER_OPEN_ANCHOR, CAREER_OPEN_REPLACEMENT, 'Career SaveSlot open')
    text = one_replace(text, SLOT_ANCHOR, SLOT_REPLACEMENT, 'initial slot 0 target')
    text = one_replace(text, POST_CREATE_ANCHOR, POST_CREATE_REPLACEMENT, 'post-create save reload')
    text = one_replace(text, FATAL_ANCHOR, FATAL_REPLACEMENT, 'fatal_check')
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
