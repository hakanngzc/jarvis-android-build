#!/usr/bin/env python3
from pathlib import Path

p = Path('stage1_public/runtime_gate_v2.sh')
if not p.exists():
    raise SystemExit('runtime_gate_v2.sh missing; run build_runtime_gate_v2.py first')
s = p.read_text()
start = s.index('# The hint was reset to -1 by p_DirectCareerLoad.')
end = s.index('# Equivalent slot2 manual reload', start)
block = s[start:end]
assert 'for decision_attempt in 1 2 3' in block, 'one-shot decision has no bounded entry retry loop'
assert 'one_shot_decision=saveslot' in block, 'one-shot decision does not explicitly require SaveSlot'
assert 'LoadCareer saveslot:[[:space:]]*2' in block, 'one-shot decision no longer guards against slot2 reload'
assert block.count('press_career_when_ready') >= 1, 'one-shot decision must use rendered entry control'
print('DIRECT_ONE_SHOT_ENTRY_RETRY_TEST=PASS')
