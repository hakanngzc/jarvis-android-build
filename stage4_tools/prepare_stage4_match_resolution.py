#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

OLD = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''
NEW = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
# Runtime-speed optimization only. Configure the half-resolution surface BEFORE
# starting a fresh process, then reload the exact baseline save. Changing wm
# size while NSS is alive can recreate the Activity while its async audio
# loader is active (run193: gxtkAudio/FlushDiscarded crash), so that unsafe
# live-resize path is forbidden here. No save/fixture/season/match state changes.
adb shell wm size 540x1140 >/dev/null
start_game natural-lowres
open_slot0 natural-lowres
load_existing natural-lowres
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

SIZE_OLD = '''size="$(adb shell wm size 2>/dev/null | tr -d '\\r')"'''
SIZE_NEW = '''size="$(adb shell wm size 2>/dev/null | tr -d '\\r' | tail -1)"'''


def harden(text: str) -> str:
    # When this preparer runs in the real workflow, Pixel4 helpers have already
    # been injected and their wm-size reads are rewritten to the effective last
    # line (Override when present, Physical otherwise). Unit tests may invoke
    # this preparer directly on the base gate before those helpers exist, so a
    # zero count is valid at that isolated layer.
    text = text.replace(SIZE_OLD, SIZE_NEW)

    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f'expected one post-baseline start anchor, found {count}')
    return text.replace(OLD, NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_match_resolution.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied pre-process half-resolution natural-match surface with effective wm-size targets: {dst}')


if __name__ == '__main__':
    main()
