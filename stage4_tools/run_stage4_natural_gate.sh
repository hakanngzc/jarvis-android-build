#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "usage: run_stage4_natural_gate.sh GATE" >&2
  exit 2
fi

GATE="$1"
[ -f "$GATE" ] || { echo "missing Stage4 gate: $GATE" >&2; exit 2; }

rc=0
for setup_attempt in 1 2 3; do
  echo "Stage4 natural gate setup attempt $setup_attempt/3"
  set +e
  bash "$GATE"
  rc=$?
  set -e
  [ "$rc" -eq 0 ] && break

  case "$rc" in
    218|219)
      mkdir -p "${RUNNER_TEMP:?}/stage4-natural"
      echo "setup-only retry after rc=$rc attempt=$setup_attempt" >> "$RUNNER_TEMP/stage4-natural/setup-retries.log"
      ;;
    *) exit "$rc";;
  esac
done

[ "$rc" -eq 0 ] || exit "$rc"
