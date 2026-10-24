#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

GM_MARKER = '''  local gm_attempt gm_play_hit=0 gm_evidence'''
GM_MISS = '''    echo "GameMenu Play attempt $gm_attempt did not register; retrying"'''

STABLE_BLOCK = '''  # LoadCareer can briefly activate GameMenu and immediately enter a stock
  # StarTransition before returning. Do not inject Play on the first GameMenu
  # log line; require the latest active surface to remain GameMenu across three
  # consecutive polls before attempting the stock Play gadget.
  local gm_settle_i gm_stable_count=0 gm_last
  for gm_settle_i in $(seq 1 12); do
    adb logcat -d -v brief > "$WORK/${scenario}-gamemenu-stability.txt" 2>/dev/null || true
    gm_last="$(grep -Ei 'SETTING ACTIVE:|SetActive:' "$WORK/${scenario}-gamemenu-stability.txt" | tail -1 || true)"
    echo "GameMenu stable poll $gm_settle_i/12: ${gm_last:-none}"
    if printf '%s\n' "$gm_last" | grep -qiE 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu'; then
      gm_stable_count=$((gm_stable_count + 1))
    else
      gm_stable_count=0
    fi
    [ "$gm_stable_count" -ge 3 ] && break
    sleep 1
  done
  [ "$gm_stable_count" -ge 3 ] || {
    cp "$WORK/${scenario}-gamemenu-stability.txt" "$OUT/${scenario}-gamemenu-stability-failed.txt" 2>/dev/null || true
    shot "${scenario}-gamemenu-stability-failed"
    echo 'GameMenu did not become stably active before Play'
    return 1
  }
  cp "$WORK/${scenario}-gamemenu-stability.txt" "$OUT/${scenario}-gamemenu-stability.txt" 2>/dev/null || true
  shot "${scenario}-gamemenu-stable"

'''

MISS_REPLACEMENT = '''    cp "$gm_evidence" "$OUT/${scenario}-gamemenu-play-attempt-${gm_attempt}.txt" 2>/dev/null || true
    shot "${scenario}-gamemenu-play-miss-${gm_attempt}"
    echo "GameMenu Play attempt $gm_attempt did not register; retrying"'''


def harden(text: str) -> str:
    marker_count = text.count(GM_MARKER)
    if marker_count != 1:
        raise SystemExit(f'expected one Stage2 GameMenu Play marker, found {marker_count}')
    miss_count = text.count(GM_MISS)
    if miss_count != 1:
        raise SystemExit(f'expected one Stage2 GameMenu Play miss marker, found {miss_count}')
    text = text.replace(GM_MARKER, STABLE_BLOCK + GM_MARKER, 1)
    text = text.replace(GM_MISS, MISS_REPLACEMENT, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage2_gamemenu_stable.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied stable-GameMenu input gate hardening: {dst}')


if __name__ == '__main__':
    main()
