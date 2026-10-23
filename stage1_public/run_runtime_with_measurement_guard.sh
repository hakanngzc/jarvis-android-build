#!/usr/bin/env bash
set -euo pipefail

mkdir -p stage1_public_artifacts/runtime
PKG=com.newstargames.newstarsoccer
MEASUREMENT="$PKG/com.google.android.gms.measurement.AppMeasurementService"
JOB_SERVICE="$PKG/com.google.android.gms.measurement.AppMeasurementJobService"
GUARD_FILE=stage1_public_artifacts/runtime/measurement-service-guard.txt

bash stage1_public/runtime_gate_v2.sh &
gate_pid=$!
guard_ok=0

for i in $(seq 1 600); do
  if adb shell pm path "$PKG" >/dev/null 2>&1; then
    {
      echo "package_seen_attempt=$i"
      adb shell pm disable-user --user 0 "$MEASUREMENT"
      adb shell pm disable-user --user 0 "$JOB_SERVICE" || true
      echo 'MEASUREMENT_SERVICE_GUARD=PASS'
    } > "$GUARD_FILE" 2>&1
    cat "$GUARD_FILE"
    guard_ok=1
    break
  fi

  if ! kill -0 "$gate_pid" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

if [ "$guard_ok" -ne 1 ]; then
  echo 'MEASUREMENT_SERVICE_GUARD=FAIL' > "$GUARD_FILE"
  cat "$GUARD_FILE"
  wait "$gate_pid" || true
  exit 126
fi

wait "$gate_pid"
