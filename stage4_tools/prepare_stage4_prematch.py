#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

OLD = '''  shot "cycle-$cycle-match"\n  clear_log; press_play 2\n  start="$(date +%s)"'''

NEW = '''  shot "cycle-$cycle-match"\n\n  # The first natural match can present a stock tutorial overlay over the\n  # prematch screen. Do not assume a Play tap starts the live match: require\n  # the authoritative stock gadget hit and retry in a bounded way if the\n  # tutorial consumes the first input.\n  local kickoff_attempt kickoff_hit=0 kickoff_evidence\n  for kickoff_attempt in 1 2 3 4; do\n    clear_log\n    echo "cycle $cycle prematch Play attempt $kickoff_attempt/4"\n    press_play 2\n    sleep 1\n    kickoff_evidence="$WORK/cycle-${cycle}-kickoff-attempt-${kickoff_attempt}.txt"\n    adb logcat -d -v brief > "$kickoff_evidence" 2>/dev/null || true\n    if grep -q 'HitGadget: match.btn_Play' "$kickoff_evidence"; then\n      kickoff_hit=1\n      capture_log "cycle $cycle stock match.btn_Play registered"\n      break\n    fi\n    fatal_check || return 1\n    shot "cycle-${cycle}-kickoff-attempt-${kickoff_attempt}"\n    echo "cycle $cycle Play attempt $kickoff_attempt was consumed before match.btn_Play; retrying"\n  done\n  [ "$kickoff_hit" -eq 1 ] || {\n    echo "cycle $cycle could not register stock match.btn_Play after 4 attempts"\n    shot "cycle-${cycle}-kickoff-failed"\n    return 1\n  }\n\n  start="$(date +%s)"'''


def harden(text: str) -> str:
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f'expected one natural prematch start block, found {count}')
    return text.replace(OLD, NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_prematch.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied stock match.btn_Play-gated prematch hardening: {dst}')


if __name__ == '__main__':
    main()
