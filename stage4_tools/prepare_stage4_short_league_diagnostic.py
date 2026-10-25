#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = """wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
clear_log; press_footer_ok 2"""

REPLACEMENT = """wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
# Setup-only diagnostic: cycle the stock 'Choose League To Play In' row and
# capture each rendered option. This does not create a Career and does not
# modify season/match state.
shot short-league-option-0
for league_step in 1 2 3 4 5 6; do
  press_logical 320 640 2
  shot \"short-league-option-$league_step\"
done
echo 'STAGE4_SHORT_LEAGUE_SELECTOR_CAPTURE=PASS' | tee \"$OUT/SHORT_LEAGUE_DIAGNOSTIC.txt\"
exit 0

clear_log; press_footer_ok 2"""


def harden(text: str) -> str:
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(f'expected one ChooseNation continue anchor, found {count}')
    return text.replace(ANCHOR, REPLACEMENT, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_short_league_diagnostic.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied setup-only short-league selector capture: {dst}')


if __name__ == '__main__':
    main()
