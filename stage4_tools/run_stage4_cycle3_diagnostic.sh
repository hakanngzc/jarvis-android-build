#!/usr/bin/env bash
set -u

GATE="${1:?usage: run_stage4_cycle3_diagnostic.sh PREPARED_GATE}"
OUT="${RUNNER_TEMP:?missing RUNNER_TEMP}/stage4-natural"

# The real Stage4 gate intentionally returns 221 when three natural cycles
# finish without reaching the season boundary. In this diagnostic that is the
# expected terminal condition; keep it inside this child wrapper so the
# emulator action can validate the evidence before exiting.
set +e
bash stage4_tools/run_stage4_natural_gate.sh "$GATE"
rc=$?
set -e

if [ "$rc" -ne 221 ]; then
  echo "cycle3 diagnostic expected Stage4 boundary-missing rc=221, got rc=$rc"
  exit "$rc"
fi

test ! -s "$OUT/runtime-fatal-logcat.txt"

for cycle in 1 2 3; do
  test -s "$OUT/cycle-$cycle-MonkeyGame.xml"
  test -s "$OUT/cycle-$cycle.json"
  grep -q "cycle $cycle natural Match -> MatchStats" "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
  grep -q "cycle $cycle postmatch -> gamemenu" "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
done

python3 - "$OUT/cycle-1.json" "$OUT/cycle-2.json" "$OUT/cycle-3.json" <<'PY'
import json,sys
rows=[json.load(open(p,encoding='utf-8')) for p in sys.argv[1:]]
apps=[int(r['careerapps']) for r in rows]
dates=[int(r['sdate']) for r in rows]
assert apps[0] >= 1, apps
assert apps[1] > apps[0], apps
assert apps[2] > apps[1], apps
assert dates[1] > dates[0], dates
assert dates[2] > dates[1], dates
print('STAGE4_CYCLE3_PROGRESS', {'careerapps': apps, 'sdate': dates})
PY

echo 'STAGE4_CYCLE3_NATURAL_DIAGNOSTIC_PASS'
