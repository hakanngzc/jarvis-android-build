#!/usr/bin/env bash
set -euo pipefail

test "$(adb shell getprop ro.build.version.release | tr -d '\r')" = "10"

python3 stage2_residual_tools/prepare_stage2_gate.py \
  stage2_residual_gate.sh "$RUNNER_TEMP/stage2-retirement-gate.pre.sh"
python3 stage2_residual_tools/prepare_runtime_start_retry.py \
  "$RUNNER_TEMP/stage2-retirement-gate.pre.sh" "$RUNNER_TEMP/stage2-retirement-gate.start.sh"
python3 stage2_residual_tools/prepare_chooseclub_visual.py \
  "$RUNNER_TEMP/stage2-retirement-gate.start.sh" "$RUNNER_TEMP/stage2-retirement-gate.visual.sh"
python3 stage2_residual_tools/prepare_stage2_gamemenu_stable.py \
  "$RUNNER_TEMP/stage2-retirement-gate.visual.sh" "$RUNNER_TEMP/stage2-retirement-gate.stable.sh"
python3 stage2_residual_tools/prepare_stage2_retirement_persistence.py \
  "$RUNNER_TEMP/stage2-retirement-gate.stable.sh" "$RUNNER_TEMP/stage2-retirement-gate.sh"

bash -n "$RUNNER_TEMP/stage2-retirement-gate.sh"
bash "$RUNNER_TEMP/stage2-retirement-gate.sh"
