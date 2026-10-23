#!/usr/bin/env python3
from pathlib import Path

p = Path('stage1_public/runtime_gate_v2.sh')
s = p.read_text()

old = '''# The hint was reset to -1 by p_DirectCareerLoad. Next Career entry must expose
# SaveSlot rather than automatically load slot2 again.
adb logcat -c >/dev/null 2>&1 || true
start_nss
wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu' 150 'MainMenu after direct hint consumed'
sleep 3
adb logcat -c >/dev/null 2>&1 || true
press_career_when_ready
wait_log 'Create Screen:[[:space:]]*saveslot|Create Screen:saveslot|LoadCareer saveslot:[[:space:]]*2' 70 'one-shot decision'
snapshot_logs
if grep -qiE 'LoadCareer saveslot:[[:space:]]*2' "$LOG"; then
  record directcareerload_one_shot FAIL
  exit 124
fi
record directcareerload_one_shot PASS
shot directcareerload-one-shot-saveslot
record DIRECTCAREERLOAD_RUNTIME PASS
'''

new = '''# The hint was reset to -1 by p_DirectCareerLoad. Next Career entry must expose
# SaveSlot rather than automatically load slot2 again. The stock title animation
# can partially occlude the rendered Play button, so retry entry from a fresh
# MainMenu frame at most three times. A real slot2 reload is still an immediate
# failure; only a no-transition click is retried.
one_shot_decision=''
for decision_attempt in 1 2 3; do
  start_nss
  if ! wait_log 'Create Screen:[[:space:]]*mainmenu|Create Screen:mainmenu' 150 "MainMenu after direct hint consumed attempt $decision_attempt"; then
    record "one_shot_attempt_${decision_attempt}" no_mainmenu
    continue
  fi
  sleep 3
  adb logcat -c >/dev/null 2>&1 || true
  press_career_when_ready
  if ! wait_log 'Create Screen:[[:space:]]*saveslot|Create Screen:saveslot|LoadCareer saveslot:[[:space:]]*2' 25 "one-shot decision attempt $decision_attempt"; then
    record "one_shot_attempt_${decision_attempt}" no_transition
    continue
  fi
  snapshot_logs
  if grep -qiE 'LoadCareer saveslot:[[:space:]]*2' "$LOG"; then
    record directcareerload_one_shot FAIL
    exit 124
  fi
  one_shot_decision=saveslot
  record one_shot_decision "$one_shot_decision"
  shot directcareerload-one-shot-saveslot
  break
done
if [ "$one_shot_decision" != saveslot ]; then
  record directcareerload_one_shot FAIL
  exit 125
fi
record directcareerload_one_shot PASS
record DIRECTCAREERLOAD_RUNTIME PASS
'''

if s.count(old) != 1:
    raise SystemExit(f'one-shot patch anchor count={s.count(old)}')
s = s.replace(old, new, 1)
p.write_text(s)
print('DIRECT_ONE_SHOT_ENTRY_RETRY_PATCH=PASS attempts=3')
