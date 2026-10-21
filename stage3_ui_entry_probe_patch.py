#!/usr/bin/env python3
from pathlib import Path

p = Path("stage3_minimal_gate.sh")
s = p.read_text(encoding="utf-8")

anchor = """# Fresh stock Career creation.
start_game fresh
open_slot0 fresh
wait_log 'Create Screen:[[:space:]]*chooseclub|SETTING ACTIVE:[[:space:]]*chooseclub|SetActive:[[:space:]]*chooseclub' 30 chooseclub"""
replacement = """# Fresh stock Career creation.
start_game fresh
open_slot0 fresh
capture_log 'ui-entry probe after slot0 tap'
shot ui-entry-after-slot0
echo 'STAGE3_UI_ENTRY_PROBE=PASS'
exit 0
wait_log 'Create Screen:[[:space:]]*chooseclub|SETTING ACTIVE:[[:space:]]*chooseclub|SetActive:[[:space:]]*chooseclub' 30 chooseclub"""

if anchor not in s:
    raise SystemExit("UI-entry probe anchor not found")

p.write_text(s.replace(anchor, replacement, 1), encoding="utf-8")
print("Applied Stage3 UI-entry probe patch")
