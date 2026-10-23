#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
case "$MODE" in
  extra-time|shootout) ;;
  *) echo 'usage: bash knockout_v4/run_knockout_v4.sh extra-time|shootout' >&2; exit 2 ;;
esac

TMP="$RUNNER_TEMP/run_knockout_v4_inner.sh"
cp knockout_v2/run_knockout_v2.sh "$TMP"
python3 - "$TMP" <<'PY'
from pathlib import Path
import sys
from knockout_v4.strip_redundant_emulator_probe import strip_redundant_emulator_probe

p = Path(sys.argv[1])
p.write_text(strip_redundant_emulator_probe(p.read_text(encoding='utf-8')), encoding='utf-8')
PY
bash -n "$TMP"
python3 -m unittest knockout_v4/test_strip_redundant_emulator_probe.py -v
bash "$TMP" "$MODE"
