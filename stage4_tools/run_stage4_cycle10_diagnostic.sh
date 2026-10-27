#!/usr/bin/env bash
set -u

GATE="${1:?usage: run_stage4_cycle10_diagnostic.sh PREPARED_GATE}"
OUT="${RUNNER_TEMP:?missing RUNNER_TEMP}/stage4-natural"

# The real Stage4 gate returns 221 when ten natural cycles finish without the
# season boundary. That is the expected terminal condition for this stress
# diagnostic. Any emulator-transport loss must escape as a distinct non-221 rc
# and leave emulator-transport-dead evidence.
set +e
bash stage4_tools/run_stage4_natural_gate.sh "$GATE"
rc=$?
set -e

if [ "$rc" -ne 221 ]; then
  echo "cycle10 diagnostic expected Stage4 boundary-missing rc=221, got rc=$rc"
  if [ -s "$OUT/emulator-transport-dead.txt" ]; then
    cat "$OUT/emulator-transport-dead.txt"
  fi
  exit "$rc"
fi

test ! -s "$OUT/runtime-fatal-logcat.txt"
test ! -s "$OUT/emulator-transport-dead.txt"

args=()
for cycle in $(seq 1 10); do
  test -s "$OUT/cycle-$cycle-MonkeyGame.xml"
  test -s "$OUT/cycle-$cycle.json"
  grep -q "cycle $cycle natural Match -> MatchStats" "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
  grep -q "cycle $cycle postmatch -> gamemenu" "$OUT/STAGE4_NATURAL_RUNTIME_FLOW.log"
  test ! -s "$OUT/cycle-$cycle-emulator-transport-dead.txt"
  args+=("$OUT/cycle-$cycle.json")
done

python3 - "${args[@]}" <<'PY'
import json,sys
rows=[json.load(open(p,encoding='utf-8')) for p in sys.argv[1:]]
apps=[int(r['careerapps']) for r in rows]
dates=[int(r['sdate']) for r in rows]
assert len(rows) == 10, len(rows)
assert apps[0] >= 1, apps
assert all(b > a for a,b in zip(apps,apps[1:])), apps
assert all(b > a for a,b in zip(dates,dates[1:])), dates
print('STAGE4_CYCLE10_PROGRESS', {'careerapps': apps, 'sdate': dates})
PY

echo 'STAGE4_CYCLE10_EMULATOR3711_STRESS_PASS'
