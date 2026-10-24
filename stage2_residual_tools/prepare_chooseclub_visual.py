#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


HELPERS = r'''press_and_require_change(){
  local tag="$1" x="$2" y="$3" before="$OUT/${tag}-before.png" after="$OUT/${tag}-after.png"
  shot "${tag}-before"
  press_logical "$x" "$y" 4
  shot "${tag}-after"
  if cmp -s "$before" "$after"; then
    echo "ChooseClub visual step did not change for $tag; pausing before one controlled retry"
    sleep 2
    press_logical "$x" "$y" 4
    shot "${tag}-retry"
  fi
  fatal_check
}
'''

# Both residual gates use this stock fresh-Career block. Replace only the blind
# repeated footer presses; the actual ChooseClub/ChooseNation screens and their
# stock m_ButtonOk methods remain untouched.
LOOP_RE = re.compile(
    r'''for _ in 1 2 3 4; do adb logcat -d -v brief > "\$WORK/setup\.txt" 2>/dev/null \|\| true; grep -qiE 'choosenation' "\$WORK/setup\.txt" && break; press_footer_ok 2; fatal_check; done\nwait_log 'Create Screen:\[\[:space:\]\]\*choosenation\|SETTING ACTIVE:\[\[:space:\]\]\*choosenation\|SetActive:\[\[:space:\]\]\*choosenation' 30 choosenation'''
)

REPLACEMENT = r'''for n in 1 2 3 4; do
  adb logcat -d -v brief > "$WORK/setup.txt" 2>/dev/null || true
  if grep -qiE 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' "$WORK/setup.txt"; then
    break
  fi
  # Proven Stage1 behavior: fresh ChooseClub first presents a help message and
  # can then perform a name-defaulting visual step before it advances. Require
  # a real frame change between presses instead of hammering the same control.
  press_and_require_change "fresh-setup-ok-$n" 536 880
 done
wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation'''


def harden_chooseclub(text: str) -> str:
    if 'press_and_require_change(){' not in text:
        anchor = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }\n'
        if anchor not in text:
            # The Stage4 source uses the same helper without stderr redirection.
            anchor = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" || true; }\n'
        if anchor not in text:
            raise SystemExit('shot helper anchor not found for visual ChooseClub hardening')
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
    print(f'Applied proven visual ChooseClub progression hardening: {dst}')


if __name__ == '__main__':
    main()
