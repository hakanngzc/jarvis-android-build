#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

# Replace only the restart/reload block inside run_scenario. The non-retirement
# branches keep their real Career -> SaveSlot -> LoadCareer path. Retirement is
# different by stock design: once m_retired is restored, MainMenu no longer
# exposes the Career entry, so forcing SaveSlot/LoadCareer is not a valid player
# path. For that branch we prove restart into stock MainMenu, then read the same
# durable slot bytes back from SharedPreferences before any further mutation.
RESTART_RE = re.compile(
    r'''(?ms)^  adb shell am force-stop "\$PKG" >/dev/null 2>&1 \|\| true\n'''
    r'''  start_game "\$scenario-restart"\n'''
    r'''  open_slot0 "\$scenario-restart"\n\n'''
    r'''  if \[ "\$scenario" = retire \]; then\n.*?'''
    r'''  else\n    load_existing "\$scenario-restart"\n  fi\n'''
    r'''  dump_save "\$scenario-post-restart"; checkpoint "\$scenario-post-restart"'''
)

RESTART_NEW = r'''  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  start_game "$scenario-restart"

  if [ "$scenario" = retire ]; then
    # Stock retirement semantics: Retirement.m_ButtonPlay QuickSaves, returns to
    # Career GameMenu, and after process restart the retired-slot metadata makes
    # MainMenu omit Career. Do not manufacture a non-player LoadCareer path.
    sleep 3
    adb logcat -d -v brief > "$OUT/retire-post-restart-mainmenu.log" 2>/dev/null || true
    grep -qiE 'Create Screen:[[:space:]]*mainmenu' "$OUT/retire-post-restart-mainmenu.log"
    grep -qiE 'SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$OUT/retire-post-restart-mainmenu.log"
    capture_log 'retire post-restart stock MainMenu retired-slot boundary'
    shot retire-post-restart-mainmenu
    dump_save "$scenario-post-restart"; checkpoint "$scenario-post-restart"
  else
    open_slot0 "$scenario-restart"
    load_existing "$scenario-restart"
    dump_save "$scenario-post-restart"; checkpoint "$scenario-post-restart"
  fi'''

EXTRA_RE = re.compile(
    r'''(?ms)^  if \[ "\$scenario" = retire \]; then\n'''
    r'''    # If runtime still allows the retired Career to be loaded, invoke the exact\n'''
    r'''    # patched PlayMatches trigger again\..*?'''
    r'''    extra\+=\(--second-after-reload "\$OUT/retire-second-after-reload\.json"\)\n'''
    r'''  fi'''
)

EXTRA_NEW = r'''  if [ "$scenario" = retire ]; then
    extra+=(--retire-mainmenu-proof "$OUT/retire-post-restart-mainmenu.log")
  fi'''


def harden(text: str) -> str:
    restart_matches = list(RESTART_RE.finditer(text))
    if len(restart_matches) != 1:
        raise SystemExit(f'expected one residual restart block, found {len(restart_matches)}')
    text = RESTART_RE.sub(lambda _m: RESTART_NEW, text, count=1)

    extra_matches = list(EXTRA_RE.finditer(text))
    if len(extra_matches) != 1:
        raise SystemExit(f'expected one obsolete retirement second-probe block, found {len(extra_matches)}')
    text = EXTRA_RE.sub(lambda _m: EXTRA_NEW, text, count=1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage2_retire_restart.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied stock retired-MainMenu restart/reload hardening: {dst}')


if __name__ == '__main__':
    main()
