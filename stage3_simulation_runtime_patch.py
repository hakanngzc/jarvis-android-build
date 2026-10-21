#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

P = Path('stage3_minimal_gate.sh')
MARKER = '# STAGE3_STOCK_SIMULATION_RUNTIME_V1'


def transform(s: str) -> str:
    if MARKER in s:
        raise ValueError('simulation runtime patch already applied')

    old_build = '''PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_stage3_fast_match_probe.py "$WORK/base-career-unsigned.apk" "$WORK/base-stage3-unsigned.apk" | tee "$OUT/stage3-fast-match-patch.txt"'''
    new_build = '''PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_debug_enabled_test.py "$WORK/base-career-unsigned.apk" "$WORK/base-stage3-unsigned.apk" | tee "$OUT/stage3-debug-enabled-patch.txt"'''
    if s.count(old_build) != 1:
        raise ValueError(f'expected one fast-match build command, found {s.count(old_build)}')
    s = s.replace(old_build, new_build, 1)

    # The normal Stage3 workflow applies stage3_match_button_target_patch.py
    # before this transform. In that form keep its already-verified tutorial
    # close helper and replace only the executable match ingress below it.
    button_anchor = '# First Career match has a tutorial overlay. Dismiss it with the already proven'
    old_anchor = '# First-time Career match can show a tutorial overlay'
    button_pos = s.find(button_anchor)
    if button_pos >= 0:
        start = s.find('MATCHSTATS_REACHED=0\n', button_pos)
        tutorial_step = r'''# Reuse the verified first-match tutorial target before touching debug autoplay.
press_match_tutorial_close 2
capture_log 'simulation tutorial closed'
shot stage3-simulation-tutorial-closed
fatal_check

'''
    else:
        start = s.find(old_anchor)
        tutorial_step = ''

    end_marker = 'shot stage3-matchstats\n'
    end = s.find(end_marker, start if start >= 0 else 0)
    if start < 0 or end < 0:
        raise ValueError('hardened MatchStats ingress anchors not found; apply Stage3 match-flow/button-target patches first')
    end += len(end_marker)

    sim_ingress = r'''# STAGE3_STOCK_SIMULATION_RUNTIME_V1
# Exact stock debug gadget from assets/monkey/NewGUI/Screens/match.uis:
# PushOrigin(226,8) + Neutral Rect(95,5,80,80) => logical center (361,53).
# DebugEnabled is exposed only in this CI test APK by patch_debug_enabled_test.py.
''' + tutorial_step + r'''SIM_TRIGGERED=0
clear_log
for i in $(seq 1 5); do
  press_logical 361 53 2
  adb logcat -d -v brief > "$WORK/simulation-trigger.log" 2>/dev/null || true
  capture_log "stock neutral simulation trigger $i"
  if grep -qiE 'HitGadget:[[:space:]]*match\.autoplayAverage|SIMULATING MATCH' "$WORK/simulation-trigger.log"; then
    SIM_TRIGGERED=1
    break
  fi
  fatal_check
  shot "stage3-simulation-trigger-$i"
done
[ "$SIM_TRIGGERED" -eq 1 ] || {
  cp "$WORK/simulation-trigger.log" "$OUT/simulation-gadget-not-triggered.log" 2>/dev/null || true
  shot stage3-simulation-gadget-not-triggered
  echo 'Stock match.autoplayAverage gadget was not triggered'
  exit 208
}

# m_SimulateMatch writes score/temp stats and sets Match/FastForward. Wait for the
# stock fast-forwarded match to hand off to MatchStats; do not call MatchOver here.
MATCHSTATS_REACHED=0
for i in $(seq 0 90); do
  fatal_check || exit 209
  adb logcat -d -v brief > "$WORK/simulation-progress.log" 2>/dev/null || true
  state="$(current_state)"
  if [ "$state" = matchstats ]; then
    MATCHSTATS_REACHED=1
    break
  fi
  sleep 1
done
capture_log 'stock neutral simulation -> MatchStats'
[ "$MATCHSTATS_REACHED" -eq 1 ] || {
  cp "$WORK/simulation-progress.log" "$OUT/simulation-matchstats-not-reached.log" 2>/dev/null || true
  shot stage3-simulation-matchstats-not-reached
  echo "Stock simulated match did not reach MatchStats; state=${state:-unknown}"
  exit 209
}
shot stage3-matchstats
'''
    s = s[:start] + sim_ingress + s[end:]

    old_verify = '''python3 stage3_tools/verify_stage3_minimal.py "$OUT/pre-match-MonkeyGame.xml" "$OUT/post-match-MonkeyGame.xml" "$OUT/post-restart-MonkeyGame.xml" "$FLOW" | tee "$OUT/STAGE3_FULL_GATE.txt"
grep -q 'STAGE3_FULL_GATE_PASS' "$OUT/STAGE3_FULL_GATE.txt"
echo 'STAGE3_MINIMAL_FULL_RUNTIME_PASS' '''.rstrip()
    new_verify = '''python3 stage3_tools/verify_stage3_simulation.py "$OUT/pre-match-MonkeyGame.xml" "$OUT/post-match-MonkeyGame.xml" "$OUT/post-restart-MonkeyGame.xml" "$FLOW" | tee "$OUT/STAGE3_SIMULATION_GATE.txt"
grep -q 'STAGE3_SIMULATION_GATE_PASS' "$OUT/STAGE3_SIMULATION_GATE.txt"
echo 'STAGE3_STOCK_SIMULATION_RUNTIME_PASS' '''.rstrip()
    if s.count(old_verify) != 1:
        raise ValueError(f'expected one minimal verifier block, found {s.count(old_verify)}')
    s = s.replace(old_verify, new_verify, 1)

    required = [
        MARKER,
        'patch_debug_enabled_test.py',
        'press_logical 361 53',
        'match\\.autoplayAverage',
        'SIMULATING MATCH',
        'verify_stage3_simulation.py',
        'STAGE3_SIMULATION_GATE_PASS',
    ]
    if not all(x in s for x in required):
        raise ValueError('simulation runtime patch postcondition failed')
    return s


def main() -> int:
    try:
        s = transform(P.read_text(encoding='utf-8'))
    except ValueError as exc:
        raise SystemExit(str(exc))
    P.write_text(s, encoding='utf-8')
    print('STAGE3_SIMULATION_RUNTIME_PATCH=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
