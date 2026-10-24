#!/usr/bin/env bash
set -euo pipefail

python3 -m py_compile stage6_public/verify_logo_render.py
bash -n stage6_public/runtime_logo_gate_v2.sh
PYTHONPATH=stage6_public python3 -m unittest stage6_public/test_verify_logo_render.py -v
exec bash stage6_public/runtime_logo_gate_v2.sh
