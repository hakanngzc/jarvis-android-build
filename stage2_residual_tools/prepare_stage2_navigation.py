#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


HELPER = r'''enter_leaguefixtures_proven(){
  local tag="$1" attempt reached=0 evidence
  for attempt in 1 2 3; do
    clear_log
    echo "LeagueFixtures entry $tag attempt $attempt/3"
    press_play 4
    if wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 7 "${tag}-leaguefixtures-attempt-${attempt}"; then
      evidence="$WORK/${tag}-leaguefixtures-attempt-${attempt}.txt"
      adb logcat -d -v brief > "$evidence" 2>/dev/null || true
      if grep -q 'HitGadget: gamemenu.btn_Play' "$evidence"; then
        reached=1
        capture_log "$tag GameMenu -> LeagueFixtures stock hit proven"
        break
      fi
      echo "LeagueFixtures reached but gamemenu.btn_Play hit was not captured for $tag attempt $attempt"
      return 1
    fi
    fatal_check || return 1
  done
  [ "$reached" -eq 1 ] || {
    shot "${tag}-leaguefixtures-failed"
    echo "LeagueFixtures not reached after 3 controlled GameMenu Play presses for $tag"
    return 1
  }
}
'''


def prepare_text(text: str) -> str:
    if 'enter_leaguefixtures_proven(){' not in text:
        anchor = 'shot(){ adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null || true; }\n'
        if anchor not in text:
            raise SystemExit('shot helper anchor not found')
        text = text.replace(anchor, anchor + HELPER + '\n', 1)

    primary_old = '''  clear_log; press_play 4
  wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 "$scenario-leaguefixtures"
  fatal_check; capture_log "$scenario GameMenu -> LeagueFixtures"
  clear_log; press_play 4; fatal_check; capture_log "$scenario mutation trigger"'''
    primary_new = '''  enter_leaguefixtures_proven "$scenario"
  clear_log; press_play 4; fatal_check; capture_log "$scenario mutation trigger"'''
    count = text.count(primary_old)
    if count != 1:
        raise SystemExit(f'expected one primary LeagueFixtures traversal, found {count}')
    return text.replace(primary_old, primary_new, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage2_navigation.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(prepare_text(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied bounded stock-hit-proven primary LeagueFixtures navigation: {dst}')


if __name__ == '__main__':
    main()
