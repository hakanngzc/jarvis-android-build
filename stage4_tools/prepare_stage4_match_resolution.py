#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

POST_BASELINE_OLD = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''
POST_BASELINE_NEW = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
# Run212 proves that changing Android wm size while NSS has active asynchronous
# audio loaders can crash stock gxtkAudio/gxtkSample with
# ArrayIndexOutOfBoundsException. Keep the already-rendered Career process at
# its stock full resolution. This is both safer and closer to player runtime.
fatal_check
rm -f "$WORK/natural-fullres-ready.png"
timeout 8s adb exec-out screencap -p > "$WORK/natural-fullres-ready.png" 2>/dev/null || true
python3 stage4_tools/validate_frame_png.py "$WORK/natural-fullres-ready.png" >> "$FLOW" 2>&1 || {
  cp "$WORK/natural-fullres-ready.png" "$OUT/natural-fullres-invalid.png" 2>/dev/null || true
  echo 'pre-season full-resolution rendered frame invalid' >> "$FLOW"
  exit 217
}
cp "$WORK/natural-fullres-ready.png" "$OUT/natural-fullres-ready.png"
test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)" || exit 216
capture_log 'natural runtime full-resolution Career -> GameMenu'
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

POST_SEASON_RESTART_OLD = '''dump_save post-season; checkpoint post-season
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game post-season-restart; open_slot0 post-season-restart; load_existing post-season-restart
dump_save post-season-restart; checkpoint post-season-restart'''
POST_SEASON_RESTART_NEW = r'''dump_save post-season; checkpoint post-season
restart_post_season_reload(){
  local restart_attempt attempt evidence mainmenu_seen startup_crashed

  for restart_attempt in 1 2; do
    mainmenu_seen=0
    startup_crashed=0
    adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
    clear_log
    rm -f "$OUT/runtime-fatal-logcat.txt"
    adb shell am start -n "$PKG/.MonkeyGame" >/dev/null

    for attempt in $(seq 1 20); do
      if ! fatal_check; then
        startup_crashed=1
        if [ -s "$OUT/runtime-fatal-logcat.txt" ]; then
          cp "$OUT/runtime-fatal-logcat.txt" "$OUT/post-season-restart-attempt-${restart_attempt}-fatal.txt" 2>/dev/null || true
          rm -f "$OUT/runtime-fatal-logcat.txt"
        fi
        echo "post-season restart attempt $restart_attempt crashed; controlled process restart" >> "$FLOW"
        break
      fi

      evidence="$WORK/post-season-restart-state.txt"
      adb logcat -d -v brief > "$evidence" 2>/dev/null || true
      if grep -q 'LoadCareer saveslot: 0' "$evidence" \
         && grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$evidence"; then
        echo 'post-season restart auto-load reached GameMenu' >> "$FLOW"
        capture_log 'post-season restart auto-load -> GameMenu'
        return 0
      fi
      if grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$evidence"; then
        mainmenu_seen=1
      fi
      sleep 1
    done

    if [ "$startup_crashed" -eq 1 ]; then
      sleep 3
      continue
    fi

    if [ "$mainmenu_seen" -eq 1 ]; then
      echo 'post-season restart auto-load not observed; using stock SaveSlot fallback' >> "$FLOW"
      open_slot0 post-season-restart
      load_existing post-season-restart
      fatal_check || return 1
      return 0
    fi

    cp "$evidence" "$OUT/post-season-restart-attempt-${restart_attempt}-state-timeout.txt" 2>/dev/null || true
    shot "post-season-restart-attempt-${restart_attempt}-state-timeout"
    echo "post-season restart attempt $restart_attempt reached neither auto-loaded GameMenu nor stable MainMenu; controlled process restart" >> "$FLOW"
    sleep 3
  done

  echo 'post-season restart failed after 2 controlled attempts' >> "$FLOW"
  return 1
}
restart_post_season_reload
dump_save post-season-restart; checkpoint post-season-restart'''

SIZE_OLD = '''size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"'''
SIZE_NEW = '''size="$(adb shell wm size 2>/dev/null | tr -d '\\r' | tail -1)"'''

LOGICAL_SIZE_OLD = '''x,y=map(float,sys.argv[1:]); s=subprocess.check_output(['adb','shell','wm','size'],text=True)
w,h=map(int,re.search(r'(\\d+)x(\\d+)',s).groups()); scale=w/640.0; top=(h-960*scale)/2.0'''
LOGICAL_SIZE_NEW = '''x,y=map(float,sys.argv[1:]); s=subprocess.check_output(['adb','shell','wm','size'],text=True)
sizes=re.findall(r'(\\d+)x(\\d+)',s)
w,h=map(int,sizes[-1]); scale=w/640.0; top=(h-960*scale)/2.0'''

BOOTSTRAP_RE = re.compile(
    r'''adb logcat -d -v threadtime > "\$WORK/bootstrap-save-proof\.txt".*?capture_log 'bootstrap-restart durable reload -> GameMenu'\s*''',
    re.S,
)
BOOTSTRAP_NEW = r'''bootstrap_saved=0
bootstrap_gamemenu=0
for bootstrap_step in $(seq 1 30); do
  fatal_check || exit 1
  adb logcat -d -v threadtime > "$WORK/bootstrap-save-proof.txt" 2>/dev/null || true
  if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState' "$WORK/bootstrap-save-proof.txt"; then
    bootstrap_saved=1
  fi
  bootstrap_state="$(latest_state)"
  echo "fresh bootstrap step ${bootstrap_step}: state=${bootstrap_state} saved=${bootstrap_saved}" >> "$FLOW"
  case "$bootstrap_state" in
    gamemenu)
      bootstrap_gamemenu=1
      break
      ;;
    dilemma|splashmessage)
      resolve_stage4_dilemma || exit 1
      ;;
    message|startransition)
      press_message_accept 2
      ;;
    webpage)
      # webpagenews.uis owns M_Footer:(ON,webpage.btn_Ok,,). Run202 proved
      # the message-button coordinate never emits a HitGadget on this screen.
      press_footer_ok 2
      ;;
    contract)
      press_footer_ok 2
      ;;
    unknown)
      # During initial Career creation the stock game can emit SAVE CAREER
      # before the following news/transition surface publishes SetActive. Give
      # it a bounded settle before classifying again; do not drive gameplay.
      sleep 2
      ;;
    *)
      echo "unexpected fresh bootstrap state: $bootstrap_state" >> "$FLOW"
      exit 218
      ;;
  esac
done
[ "$bootstrap_saved" -eq 1 ] || {
  cp "$WORK/bootstrap-save-proof.txt" "$OUT/bootstrap-save-proof-missing.txt" 2>/dev/null || true
  echo 'Fresh Career save evidence missing'
  exit 1
}
[ "$bootstrap_gamemenu" -eq 1 ] || {
  adb logcat -d -v threadtime > "$OUT/bootstrap-gamemenu-timeout.txt" 2>/dev/null || true
  echo 'Fresh Career did not finish stock bootstrap to GameMenu'
  exit 219
}
capture_log 'fresh Career durable SAVE CAREER confirmed -> GameMenu'
'''


def harden(text: str) -> str:
    # Stage2's shared persistence hardener adds a baseline restart that is useful
    # for Stage2 branch persistence but redundant for Stage4's in-process natural
    # season. The final post-season restart/reload remains mandatory below.
    matches = list(BOOTSTRAP_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one shared bootstrap-restart block, found {len(matches)}')
    text = BOOTSTRAP_RE.sub(BOOTSTRAP_NEW, text, count=1)

    # Keep size parsing robust even though the natural gate no longer applies a
    # wm override. Other runtime environments can still report multiple size
    # lines, so use the effective final line consistently.
    text = text.replace(SIZE_OLD, SIZE_NEW)

    logical_count = text.count(LOGICAL_SIZE_OLD)
    if logical_count != 1:
        raise SystemExit(f'expected one logical_xy wm-size parser, found {logical_count}')
    text = text.replace(LOGICAL_SIZE_OLD, LOGICAL_SIZE_NEW, 1)

    restart_count = text.count(POST_SEASON_RESTART_OLD)
    if restart_count != 1:
        raise SystemExit(f'expected one final post-season restart block, found {restart_count}')
    text = text.replace(POST_SEASON_RESTART_OLD, POST_SEASON_RESTART_NEW, 1)

    count = text.count(POST_BASELINE_OLD)
    if count != 1:
        raise SystemExit(f'expected one post-baseline start anchor, found {count}')
    return text.replace(POST_BASELINE_OLD, POST_BASELINE_NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_match_resolution.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied Stage4 full-resolution natural-season runtime hardening: {dst}')


if __name__ == '__main__':
    main()
