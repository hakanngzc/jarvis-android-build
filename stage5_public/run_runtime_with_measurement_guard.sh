#!/usr/bin/env bash
set -euo pipefail

mkdir -p stage5_public_artifacts/runtime
PKG=com.newstargames.newstarsoccer
MEASUREMENT="$PKG/com.google.android.gms.measurement.AppMeasurementService"
JOB_SERVICE="$PKG/com.google.android.gms.measurement.AppMeasurementJobService"
GUARD_FILE=stage5_public_artifacts/runtime/measurement-service-guard.txt
SUMMARY=stage5_public_artifacts/runtime/stage5-gates.txt

rm -f "$GUARD_FILE"
setsid bash stage5_public/runtime_name_save_compat.sh &
gate_pid=$!

gate_group_cleanup(){
  kill -CONT -- -"$gate_pid" >/dev/null 2>&1 || true
  kill -TERM -- -"$gate_pid" >/dev/null 2>&1 || true
  sleep 0.2
  kill -KILL -- -"$gate_pid" >/dev/null 2>&1 || true
}
trap gate_group_cleanup EXIT INT TERM

guard_ready=0
for i in $(seq 1 900); do
  if [ -f "$SUMMARY" ] && grep -q '^test_fixture_installed=PASS$' "$SUMMARY"; then
    echo "fixture_ready_attempt=$i" > "$GUARD_FILE"
    guard_ready=1
    break
  fi
  if ! kill -0 "$gate_pid" >/dev/null 2>&1; then
    break
  fi
  sleep 0.1
done

if [ "$guard_ready" -ne 1 ]; then
  echo 'MEASUREMENT_SERVICE_GUARD=FAIL fixture_not_ready' >> "$GUARD_FILE"
  cat "$GUARD_FILE"
  if wait "$gate_pid"; then exit 126; else exit $?; fi
fi

kill -STOP -- -"$gate_pid"

if ! adb root >> "$GUARD_FILE" 2>&1; then
  echo 'MEASUREMENT_SERVICE_GUARD=FAIL adb_root' >> "$GUARD_FILE"
  cat "$GUARD_FILE"
  exit 127
fi
adb wait-for-device
sleep 1

if ! adb shell pm disable-user --user 0 "$MEASUREMENT" >> "$GUARD_FILE" 2>&1; then
  echo 'MEASUREMENT_SERVICE_GUARD=FAIL measurement_disable' >> "$GUARD_FILE"
  cat "$GUARD_FILE"
  exit 128
fi
adb shell pm disable-user --user 0 "$JOB_SERVICE" >> "$GUARD_FILE" 2>&1 || true
echo 'MEASUREMENT_SERVICE_GUARD=PASS' >> "$GUARD_FILE"
cat "$GUARD_FILE"

kill -CONT -- -"$gate_pid"

if wait "$gate_pid"; then
  gate_rc=0
else
  gate_rc=$?
fi
trap - EXIT INT TERM
exit "$gate_rc"
