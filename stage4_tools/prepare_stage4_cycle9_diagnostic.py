#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

BOOTSTRAP_RE = re.compile(
    r'''start_game fresh; open_slot0 fresh\n.*?BASE_FLOW_BYTES="\$\(wc -c < "\$FLOW"\)"\nSTART_EPOCH="\$\(date \+%s\)"; SEASON_SEEN=0; CYCLES=0''',
    re.S,
)

BOOTSTRAP_NEW = r'''diagnostic_load_cycle9_seed(){
  local uid gid attempt loaded=0 game=0 main=0
  : "${STAGE4_DIAGNOSTIC_SEED:?missing STAGE4_DIAGNOSTIC_SEED}"
  [ -s "$STAGE4_DIAGNOSTIC_SEED" ] || { echo 'diagnostic seed missing'; return 1; }

  # Prime the freshly installed stock APK once so its normal Android/runtime
  # directories and first-start state are initialized before replacing slot0.
  start_game diagnostic-prime || return 1
  adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
  adb root >/dev/null 2>&1 || true
  adb wait-for-device
  adb shell mkdir -p "/data/data/$PKG/shared_prefs"
  adb push "$STAGE4_DIAGNOSTIC_SEED" /data/local/tmp/stage4-cycle9-MonkeyGame.xml >/dev/null
  uid="$(adb shell stat -c %u "/data/data/$PKG" | tr -d '\r')"
  gid="$(adb shell stat -c %g "/data/data/$PKG" | tr -d '\r')"
  adb shell cp /data/local/tmp/stage4-cycle9-MonkeyGame.xml "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  adb shell chown "$uid:$gid" "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  adb shell chmod 660 "/data/data/$PKG/shared_prefs/MonkeyGame.xml"
  adb shell restorecon "/data/data/$PKG/shared_prefs/MonkeyGame.xml" >/dev/null 2>&1 || true

  clear_log
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null
  for attempt in $(seq 1 25); do
    fatal_check || return 1
    adb logcat -d -v brief > "$WORK/diagnostic-reload.txt" 2>/dev/null || true
    grep -q 'LoadCareer saveslot: 0' "$WORK/diagnostic-reload.txt" && loaded=1 || true
    grep -qiE 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/diagnostic-reload.txt" && game=1 || true
    grep -qiE 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' "$WORK/diagnostic-reload.txt" && main=1 || true
    if [ "$loaded" -eq 1 ] && [ "$game" -eq 1 ]; then
      echo 'diagnostic cycle9 seed auto-load reached GameMenu' >> "$FLOW"
      capture_log 'DIAGNOSTIC ONLY cycle9 seed -> GameMenu'
      return 0
    fi
    sleep 1
  done

  if [ "$main" -eq 1 ]; then
    echo 'diagnostic cycle9 seed restart stayed at MainMenu; using stock slot0 fallback' >> "$FLOW"
    open_slot0 diagnostic-seed || return 1
    load_existing diagnostic-seed || return 1
    return 0
  fi

  cp "$WORK/diagnostic-reload.txt" "$OUT/diagnostic-seed-reload-failed.txt" 2>/dev/null || true
  shot diagnostic-seed-reload-failed
  return 1
}

diagnostic_load_cycle9_seed || exit 230
dump_save natural-baseline; checkpoint natural-baseline
echo 'STAGE4_DIAGNOSTIC_ONLY_SEEDED_FROM_RUN275_CYCLE9' >> "$FLOW"
BASE_FLOW_BYTES="$(wc -c < "$FLOW")"
START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0'''

FINAL_RE = re.compile(
    r'''\[ "\$SEASON_SEEN" -eq 1 \] \|\| \{ echo "Natural season boundary not observed after \$CYCLES cycles"; exit 221; \}\n\n.*?echo 'STAGE4_NATURAL_SEASON_PASS'\n?''',
    re.S,
)

FINAL_NEW = r'''[ "$SEASON_SEEN" -eq 1 ] || { echo "Diagnostic season boundary not observed after $CYCLES resumed cycles"; exit 221; }
dump_save diagnostic-boundary; checkpoint diagnostic-boundary
echo "STAGE4_DIAGNOSTIC_BOUNDARY_REACHED resumed_cycles=$CYCLES" | tee "$OUT/STAGE4_DIAGNOSTIC_RESULT.txt"
# Deliberately never run the final natural-season verifier here. This seeded
# continuation is blocker discovery only and can never constitute Stage4 PASS.
'''


def harden(text: str) -> str:
    matches = list(BOOTSTRAP_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one composed fresh bootstrap block, found {len(matches)}')
    text = BOOTSTRAP_RE.sub(BOOTSTRAP_NEW, text, count=1)
    matches = list(FINAL_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one final verifier block, found {len(matches)}')
    text = FINAL_RE.sub(FINAL_NEW, text, count=1)
    if 'STAGE4_NATURAL_SEASON_PASS' in text:
        raise SystemExit('diagnostic script must never contain natural PASS literal')
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_cycle9_diagnostic.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Prepared seeded cycle9 diagnostic-only continuation: {dst}')


if __name__ == '__main__':
    main()
