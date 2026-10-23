#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=stage6_public python3 -m unittest stage6_public/test_verify_logo_render.py -v
exec bash stage6_public/runtime_logo_gate_v2.sh
