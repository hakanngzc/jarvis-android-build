#!/usr/bin/env bash
set -u

GATE="${1:?usage: run_stage4_cycle1_diagnostic.sh PREPARED_GATE}"
OUT="${RUNNER_TEMP:?missing RUNNER_TEMP}/stage4-natural"

# The real Stage4 gate intentionally returns 221 when one natural cycle finishes
# without reaching the season boundary. In this diagnostic that is the expected
# terminal condition; keep it inside this child wrapper so the emulator action
# does not abort before evidence validation can run.
set +e
bash stage4_tools/run_stage4_natural_gate.sh "$GATE"
rc=$?
set -e

if [ "$rc" -ne 221 ]; then
  echo "cycle1 diagnostic expected Stage4 boundary-missing rc=221, got rc=$rc"
  exit "$rc"
fi

test -s "$OUT/cycle-1-MonkeyGame.xml"
test -s "$OUT/cycle-1.json"
test ! -s "$OUT/runtime-fatal-logcat.txt"
grep -q 'cycle 1 natural Match -> MatchStats' "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
grep -q 'cycle 1 postmatch -> gamemenu' "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"

python3 - "$OUT/cycle-1.json" <<'PY'
import json,sys
p=sys.argv[1]
data=json.load(open(p,encoding='utf-8'))
assert int(data['careerapps']) >= 1, data
PY

if grep -q 'SETTING ACTIVE:[[:space:]]*ratings' "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"; then
  grep -q 'cycle 1 postmatch -> ratings' "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
  echo 'STAGE4_CYCLE1_RATINGS_PATH_OBSERVED'
else
  echo 'STAGE4_CYCLE1_RATINGS_PATH_NOT_OBSERVED'
fi

echo 'STAGE4_CYCLE1_NATURAL_DIAGNOSTIC_PASS'
