#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

POST_BASELINE_OLD = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''
POST_BASELINE_NEW = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
# Run205 proved that Android's wm-size override recreates the NSS Activity and
# returns the stock UI to MainMenu. Keep the lower rendered resolution for the
# long natural-match loop, but explicitly reload the already-saved Career
# through stock MainMenu -> SaveSlot -> LoadCareer before driving fixtures.
# No save field, fixture, season date, competition state or match method is
# patched by this transition.
clear_log
adb shell wm size 540x1140 >/dev/null
wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 30 natural-lowres-mainmenu || {
  adb logcat -d -v threadtime > "$OUT/natural-lowres-mainmenu-timeout.txt" 2>/dev/null || true
  echo 'wm-size recreation did not reach stock MainMenu'
  exit 215
}
fatal_check
open_slot0 natural-lowres
load_existing natural-lowres
fatal_check
rm -f "$WORK/natural-lowres-ready.png"
timeout 8s adb exec-out screencap -p > "$WORK/natural-lowres-ready.png" 2>/dev/null || true
python3 stage4_tools/validate_frame_png.py "$WORK/natural-lowres-ready.png" >> "$FLOW" 2>&1 || {
  cp "$WORK/natural-lowres-ready.png" "$OUT/natural-lowres-invalid.png" 2>/dev/null || true
  echo 'post-reload low-resolution rendered frame invalid' >> "$FLOW"
  exit 217
}
cp "$WORK/natural-lowres-ready.png" "$OUT/natural-lowres-ready.png"
test -n "$(adb shell pidof "$PKG" | tr -d '\\r' || true)" || exit 216
capture_log 'natural runtime resize -> stock Career reload -> GameMenu'
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

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
    # for Stage2 branch persistence but redundant before the Stage4 resize. The
    # resize itself has a stock Career reload because Android recreates Activity.
    matches = list(BOOTSTRAP_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one shared bootstrap-restart block, found {len(matches)}')
    text = BOOTSTRAP_RE.sub(BOOTSTRAP_NEW, text, count=1)

    # If an Android wm override exists, use the effective final size line so
    # generated helpers fall back to scalable logical coordinates rather than
    # stale full-Pixel4 physical coordinates.
    text = text.replace(SIZE_OLD, SIZE_NEW)

    # logical_xy parses `wm size` directly in Python. With an override Android
    # prints physical first and override second; re.search therefore kept the
    # stale 1080x2280 geometry and run205 injected out-of-bounds touches after
    # resizing to 540x1140. Require exactly one helper and use the final size.
    logical_count = text.count(LOGICAL_SIZE_OLD)
    if logical_count != 1:
        raise SystemExit(f'expected one logical_xy wm-size parser, found {logical_count}')
    text = text.replace(LOGICAL_SIZE_OLD, LOGICAL_SIZE_NEW, 1)

    count = text.count(POST_BASELINE_OLD)
    if count != 1:
        raise SystemExit(f'expected one post-baseline start anchor, found {count}')
    return text.replace(POST_BASELINE_OLD, POST_BASELINE_NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_match_resolution.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied Stage4 resize-safe logical input plus stock Career reload: {dst}')


if __name__ == '__main__':
    main()
