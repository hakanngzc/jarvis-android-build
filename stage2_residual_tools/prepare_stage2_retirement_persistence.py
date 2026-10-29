#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

BUILD_BLOCK = '''build_probe accept
build_probe reject
build_probe transfer "$DEST_CLUB"
build_probe retire'''
BUILD_REPLACEMENT = '''build_probe retire'''

RESTART_BLOCK = '''  if [ "$scenario" = retire ]; then
    # A retired slot may remain on SaveSlot instead of entering GameMenu. Opening
    # SaveSlot is still the stock runtime metadata reload boundary; raw Career
    # state is then checked and a second stock ButtonPlay no-op is attempted only
    # if LoadCareer remains available.
    sleep 3; capture_log 'retire post-restart SaveSlot metadata'; shot retire-post-restart-saveslot
    adb logcat -d -v brief > "$WORK/retire-restart-state.txt" 2>/dev/null || true
    if grep -q 'LoadCareer saveslot: 0' "$WORK/retire-restart-state.txt"; then
      wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 30 retire-reload-gamemenu || true
    fi
  else
    load_existing "$scenario-restart"
  fi'''
RESTART_REPLACEMENT = '''  if [ "$scenario" = retire ]; then
    sleep 3
    capture_log 'retire post-restart SaveSlot metadata'
    shot retire-post-restart-saveslot
    wait_log 'LoadCareer saveslot: 0' 30 retire-loadcareer
    wait_log '>>>> RETIRED' 30 retire-retired
    fatal_check
    capture_log 'retire stock reload retired state'
  else
    load_existing "$scenario-restart"
  fi'''

VERIFY_BLOCK = '''  extra=()
  if [ "$scenario" = transfer ]; then extra+=(--destination-club-id "$dest"); fi
  if [ "$scenario" = retire ]; then
    # If runtime still allows the retired Career to be loaded, invoke the exact
    # patched PlayMatches trigger again. GameMenu Play first opens LeagueFixtures;
    # the second Play reaches the authoritative stock Retirement.m_ButtonPlay.
    # Because m_retired was restored nonzero, the second writer execution must
    # leave the durable Career checkpoint unchanged.
    if grep -q 'LoadCareer saveslot: 0' "$WORK/retire-restart-state.txt"; then
      clear_log
      press_play 3
      wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 retire-second-leaguefixtures
      fatal_check
      capture_log 'retire second probe GameMenu -> LeagueFixtures'
      clear_log
      press_play 3
      sleep 3
      fatal_check
      capture_log 'retire second stock retirement writer no-op'
      dump_save retire-second-after-reload
      checkpoint retire-second-after-reload
    else
      cp "$OUT/retire-post-restart.json" "$OUT/retire-second-after-reload.json"
    fi
    extra+=(--second-after-reload "$OUT/retire-second-after-reload.json")
  fi

  python3 stage2_residual_tools/verify_stage2_residual.py \\
    --scenario "$scenario" --base "$OUT/baseline.json" \\
    --post "$OUT/$scenario-post.json" --restart "$OUT/$scenario-post-restart.json" \\
    "${extra[@]}" --out "$OUT/$scenario-verdict.json" | tee "$OUT/$scenario-verdict.txt"'''
VERIFY_REPLACEMENT = '''  python3 stage2_residual_tools/verify_stage2_retirement_persistence.py \\
    --base "$OUT/baseline.json" \\
    --post "$OUT/retire-post.json" \\
    --restart "$OUT/retire-post-restart.json" \\
    --post-xml "$OUT/retire-post-MonkeyGame.xml" \\
    --restart-xml "$OUT/retire-post-restart-MonkeyGame.xml" \\
    --flow "$FLOW" \\
    --out "$OUT/retire-persistence-verdict.json" | tee "$OUT/retire-persistence-verdict.txt"'''

BOTTOM_BLOCK = '''run_scenario accept
run_scenario reject
run_scenario transfer "$DEST_CLUB"
run_scenario retire

grep -q 'STAGE2_ACCEPT_RESTART_RELOAD_PASS' "$OUT/accept-verdict.txt"
grep -q 'STAGE2_REJECT_RESTART_RELOAD_PASS' "$OUT/reject-verdict.txt"
grep -q 'STAGE2_TRANSFER_RESTART_RELOAD_PASS' "$OUT/transfer-verdict.txt"
grep -q 'STAGE2_RETIRE_RESTART_RELOAD_PASS' "$OUT/retire-verdict.txt"
fatal_check

echo 'STAGE2_RESIDUAL_RUNTIME_PASS' | tee "$OUT/STAGE2_RESIDUAL_RUNTIME_RESULT.txt"'''
BOTTOM_REPLACEMENT = '''run_scenario retire

grep -q 'STAGE2_RETIREMENT_PERSISTENCE_PASS' "$OUT/retire-persistence-verdict.txt"
fatal_check

echo 'STAGE2_RETIREMENT_PERSISTENCE_RUNTIME_PASS' | tee "$OUT/STAGE2_RETIREMENT_PERSISTENCE_RUNTIME_RESULT.txt"'''


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f'expected exactly one {label} block, found {count}')
    return text.replace(old, new, 1)


def prepare(text: str) -> str:
    text = _replace_once(text, BUILD_BLOCK, BUILD_REPLACEMENT, 'probe-build')
    text = _replace_once(text, RESTART_BLOCK, RESTART_REPLACEMENT, 'retirement restart')
    text = _replace_once(text, VERIFY_BLOCK, VERIFY_REPLACEMENT, 'scenario verifier')
    text = _replace_once(text, BOTTOM_BLOCK, BOTTOM_REPLACEMENT, 'scenario runner')
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage2_retirement_persistence.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(prepare(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Prepared retirement-only persistence gate: {dst}')


if __name__ == '__main__':
    main()
