#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


HELPERS = r'''press_and_require_stock_hit(){
  local tag="$1" x="$2" y="$3" attempt evidence size
  size="$(adb shell wm size 2>/dev/null | tr -d '\r')"
  for attempt in 1 2 3; do
    clear_log
    shot "${tag}-attempt-${attempt}-before"

    if [[ "$size" == *1080x2280* ]]; then
      case "$tag" in
        fresh-setup-ok-1)
          # Artifact run132 proves the 1080x2280 Welcome/help green button spans
          # about x=560..1050, y=1714..1978; use its measured center.
          case "$attempt" in
            1)
              echo "setup $tag attempt $attempt: Pixel4 welcome/help checkmark target 805,1845"
              adb shell input touchscreen tap 805 1845 </dev/null || true
              sleep 4
              ;;
            *)
              adb shell input touchscreen swipe 805 1845 805 1845 220 </dev/null || true
              sleep 4
              ;;
          esac
          ;;
        fresh-setup-ok-2|fresh-setup-ok-3)
          # Run190 proves the player-profile surface can be setup step 2, while
          # run122 observed it as step 3. Do not bind this real rendered screen
          # to one incidental setup index: both use the measured white Next
          # football center at about 940,1830 on 1080x2280 Pixel4.
          echo "setup $tag attempt $attempt: Pixel4 player-profile Next target 940,1830"
          if [ "$attempt" = 1 ]; then
            adb shell input touchscreen tap 940 1830 </dev/null || true
          else
            adb shell input touchscreen swipe 940 1830 940 1830 220 </dev/null || true
          fi
          sleep 4
          ;;
        *)
          # ChooseClub and any later ordinary footer screen keep the stock
          # logical footer target.
          press_logical "$x" "$y" 4
          ;;
      esac
    else
      press_logical "$x" "$y" 4
    fi

    shot "${tag}-attempt-${attempt}-after"
    evidence="$WORK/${tag}-attempt-${attempt}.txt"
    adb logcat -d -v brief > "$evidence" 2>/dev/null || true
    if grep -qE 'HitGadget: (message|chooseclub)\.btn_Ok|Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' "$evidence"; then
      capture_log "$tag stock setup input registered"
      return 0
    fi
    cp "$evidence" "$OUT/${tag}-attempt-${attempt}.txt" 2>/dev/null || true
    fatal_check || return 1
    echo "setup control did not register for $tag attempt $attempt/3"
    sleep 2
  done
  echo "setup control did not register for $tag after 3 controlled attempts"
  return 1
}
'''

# Both residual gates use this stock fresh-Career block. Replace only the blind
# repeated footer presses; the actual game screens and their stock handlers
# remain untouched. Screen animations/tickers are not accepted as input proof:
# each controlled press must produce a stock gadget hit or the real
# ChooseNation transition.
LOOP_RE = re.compile(
    r'''for _ in 1 2 3 4; do adb logcat -d -v brief > "\$WORK/setup\.txt" 2>/dev/null \|\| true; grep -qiE 'choosenation' "\$WORK/setup\.txt" && break; press_footer_ok 2; fatal_check; done\nwait_log 'Create Screen:\[\[:space:\]\]\*choosenation\|SETTING ACTIVE:\[\[:space:\]\]\*choosenation\|SetActive:\[\[:space:\]\]\*choosenation' 30 choosenation'''
)

REPLACEMENT = r'''for n in 1 2 3 4 5 6; do
  adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true
  if grep -qiE 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' "$WORK/setup.txt"; then
    break
  fi
  # Fresh Career setup includes distinct stock surfaces before nationality.
  # Use step-specific Pixel4 targets only where artifact evidence identifies
  # those surfaces, and keep stock event/transition proof as the success gate.
  press_and_require_stock_hit "fresh-setup-ok-$n" 536 880
 done
wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation'''


def harden_chooseclub(text: str) -> str:
    if 'press_and_require_stock_hit(){' not in text:
        anchor = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }\n'
        if anchor not in text:
            anchor = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" || true; }\n'
        if anchor not in text:
            raise SystemExit('shot helper anchor not found for stock-hit ChooseClub hardening')
        text = text.replace(anchor, anchor + HELPERS + '\n', 1)

    matches = list(LOOP_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one blind ChooseClub setup loop, found {len(matches)}')
    return LOOP_RE.sub(REPLACEMENT, text, count=1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_chooseclub_visual.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    hardened = harden_chooseclub(src.read_text(encoding='utf-8'))
    dst.write_text(hardened, encoding='utf-8')
    print(f'Applied stock-hit-proven ChooseClub progression hardening: {dst}')


if __name__ == '__main__':
    main()
