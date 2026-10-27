#!/usr/bin/env bash
set -u

GATE="${1:?usage: run_stage4_main329_pin_cycle1.sh PREPARED_GATE}"
OUT="${RUNNER_TEMP:?missing RUNNER_TEMP}/stage4-natural"

set +e
bash stage4_tools/run_stage4_natural_gate.sh "$GATE"
rc=$?
set -e

if [ "$rc" -ne 221 ]; then
  echo "main329 pin cycle1 expected boundary-missing rc=221, got rc=$rc"
  test ! -s "$OUT/runtime-transport-dead.txt" || cat "$OUT/runtime-transport-dead.txt"
  exit "$rc"
fi

test -s "$OUT/natural-baseline.json"
test -s "$OUT/cycle-1.json"
test -s "$OUT/cycle-1-MonkeyGame.xml"
test ! -s "$OUT/runtime-fatal-logcat.txt"
test ! -s "$OUT/runtime-transport-dead.txt"
grep -q 'cycle 1 natural Match -> MatchStats' "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
grep -q 'cycle 1 postmatch -> gamemenu' "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"

python3 - "$OUT/natural-baseline.json" "$OUT/cycle-1.json" <<'PY'
import json,sys
base=json.load(open(sys.argv[1],encoding='utf-8'))
cycle=json.load(open(sys.argv[2],encoding='utf-8'))
assert int(base['careerapps']) == 0, base
assert int(base['sdate']) == 36, base
assert int(cycle['careerapps']) > int(base['careerapps']), (base,cycle)
assert int(cycle['sdate']) > int(base['sdate']), (base,cycle)
print('STAGE4_MAIN329_PIN_CYCLE1_PROGRESS', {
    'careerapps': [base['careerapps'], cycle['careerapps']],
    'sdate': [base['sdate'], cycle['sdate']],
})
PY

echo 'STAGE4_MAIN329_PIN_CYCLE1_PASS'
