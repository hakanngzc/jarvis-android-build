#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

OLD = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''
NEW = '''BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
# Runtime-speed optimization only. The natural-baseline checkpoint is already
# taken after bootstrap-restart loaded this exact Career through stock
# LoadCareer and returned to GameMenu. Run193 proved an additional immediate
# restart/load can race NSS 4.31's async sound loader (gxtkSample.FlushDiscarded).
# Keep the proven loaded state and only reduce rendered pixels; no save field,
# fixture, season date, match method or game-state value changes.
adb shell wm size 540x1140 >/dev/null
sleep 3
fatal_check
capture_log 'natural runtime render surface -> 540x1140'
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''


def harden(text: str) -> str:
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f'expected one post-baseline start anchor, found {count}')
    return text.replace(OLD, NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_match_resolution.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied post-baseline in-process half-resolution natural-match surface: {dst}')


if __name__ == '__main__':
    main()
