#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

OLD = '''      clear_log
      press_play 3
      wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 retire-second-leaguefixtures
      fatal_check
      capture_log 'retire second probe GameMenu -> LeagueFixtures'
      clear_log
      press_play 3
      sleep 3
      fatal_check
      capture_log 'retire second stock retirement writer no-op' '''.rstrip()

NEW = '''      local second_gm_attempt second_gm_hit=0 second_gm_evidence
      for second_gm_attempt in 1 2 3; do
        clear_log
        echo "retire second GameMenu Play attempt $second_gm_attempt/3"
        press_play 3
        second_gm_evidence="$WORK/retire-second-gamemenu-play-attempt-${second_gm_attempt}.txt"
        adb logcat -d -v brief > "$second_gm_evidence" 2>/dev/null || true
        if grep -q 'HitGadget: gamemenu.btn_Play' "$second_gm_evidence"; then
          second_gm_hit=1
          break
        fi
        fatal_check || return 1
        echo "retire second GameMenu Play attempt $second_gm_attempt did not register; retrying"
      done
      [ "$second_gm_hit" -eq 1 ] || {
        echo 'retire second GameMenu Play did not register after 3 controlled presses'
        return 1
      }
      wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 retire-second-leaguefixtures
      fatal_check
      capture_log 'retire second probe GameMenu -> LeagueFixtures'

      local second_lf_attempt second_lf_hit=0 second_lf_evidence
      for second_lf_attempt in 1 2 3; do
        clear_log
        echo "retire second LeagueFixtures Play attempt $second_lf_attempt/3"
        press_play 3
        second_lf_evidence="$WORK/retire-second-leaguefixtures-play-attempt-${second_lf_attempt}.txt"
        adb logcat -d -v brief > "$second_lf_evidence" 2>/dev/null || true
        if grep -q 'HitGadget: leaguefixtures.btn_Play' "$second_lf_evidence"; then
          second_lf_hit=1
          break
        fi
        fatal_check || return 1
        echo "retire second LeagueFixtures Play attempt $second_lf_attempt did not register; retrying"
      done
      [ "$second_lf_hit" -eq 1 ] || {
        echo 'retire second LeagueFixtures Play did not register after 3 controlled presses'
        return 1
      }
      sleep 3
      fatal_check
      capture_log 'retire second stock retirement writer no-op' '''.rstrip()


def harden(text: str) -> str:
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f'expected one retirement reload Play block, found {count}')
    return text.replace(OLD, NEW, 1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage2_retire_second.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied stock-hit-proven retirement reload writer hardening: {dst}')


if __name__ == '__main__':
    main()
