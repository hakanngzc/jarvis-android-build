#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
case "$MODE" in
  extra-time|shootout) ;;
  *) echo 'usage: bash knockout_v5/run_knockout_v5.sh extra-time|shootout' >&2; exit 2 ;;
esac

TMP="$RUNNER_TEMP/run_knockout_v5_inner.sh"
cp knockout_v2/run_knockout_v2.sh "$TMP"
python3 - "$TMP" <<'PY'
from pathlib import Path
import sys
from knockout_v4.strip_redundant_emulator_probe import strip_redundant_emulator_probe

p = Path(sys.argv[1])
text = strip_redundant_emulator_probe(p.read_text(encoding='utf-8'))
old = 'stage3/pick_mainmenu_play.py'
count = text.count(old)
if count != 2:
    raise SystemExit(f'expected exactly two MainMenu picker references, found {count}')
text = text.replace(old, 'knockout_v5/pick_mainmenu_play.py')
p.write_text(text, encoding='utf-8')
PY
bash -n "$TMP"
python3 -m unittest knockout_v5/test_pick_mainmenu_play.py -v
python3 -m unittest knockout_v4/test_strip_redundant_emulator_probe.py -v
bash "$TMP" "$MODE"
