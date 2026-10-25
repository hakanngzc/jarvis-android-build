#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ANCHOR = """wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
clear_log; press_footer_ok 2"""

REPLACEMENT = """wait_log 'Create Screen:[[:space:]]*choosenation|SETTING ACTIVE:[[:space:]]*choosenation|SetActive:[[:space:]]*choosenation' 30 choosenation
# Natural-season setup optimization only: use the stock rendered league picker
# to choose Andorra, a shorter real league. No save field, season date, fixture,
# competition state, match engine or simulate/debug method is patched.
press_logical 320 640 2
shot short-league-list-open
press_logical 320 400 2
shot short-league-andorra-selected
clear_log; press_footer_ok 2"""


def harden(text: str) -> str:
    count = text.count(ANCHOR)
    if count != 1:
        raise SystemExit(f'expected one ChooseNation continue anchor, found {count}')
    return text.replace(ANCHOR, REPLACEMENT, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_short_league.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied stock-UI Andorra short-league selection: {dst}')


if __name__ == '__main__':
    main()
