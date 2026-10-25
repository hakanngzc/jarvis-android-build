#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

BASE_OLD = '''dump_save natural-baseline; checkpoint natural-baseline
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''
BASE_NEW = '''dump_save natural-baseline; checkpoint natural-baseline
# Only season-transition evidence emitted after the baseline checkpoint counts.
# This excludes NewSeasonSetUp markers that may occur during fresh-Career bootstrap.
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

CHECK_OLD = '''  adb logcat -d -v brief >> "$FLOW" 2>/dev/null || true
  if grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp1' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp2' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp3' "$FLOW" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp4' "$FLOW"; then
    SEASON_SEEN=1; break
  fi'''
CHECK_NEW = '''  adb logcat -d -v brief >> "$FLOW" 2>/dev/null || true
  tail -c +$((BASE_FLOW_BYTES + 1)) "$FLOW" > "$WORK/post-baseline-season-flow.log" 2>/dev/null || true
  if grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp1' "$WORK/post-baseline-season-flow.log" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp2' "$WORK/post-baseline-season-flow.log" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp3' "$WORK/post-baseline-season-flow.log" && grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp4' "$WORK/post-baseline-season-flow.log"; then
    SEASON_SEEN=1; break
  fi'''


def harden(text: str) -> str:
    if text.count(BASE_OLD) != 1:
        raise SystemExit(f'expected one baseline marker anchor, found {text.count(BASE_OLD)}')
    text = text.replace(BASE_OLD, BASE_NEW, 1)
    if text.count(CHECK_OLD) != 1:
        raise SystemExit(f'expected one season marker check anchor, found {text.count(CHECK_OLD)}')
    text = text.replace(CHECK_OLD, CHECK_NEW, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_boundary_scope.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied post-baseline-only natural season marker scope: {dst}')


if __name__ == '__main__':
    main()
