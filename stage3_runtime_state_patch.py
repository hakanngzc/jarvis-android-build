#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

MARKER = '# STAGE3_MULTI_SIGNAL_RUNTIME_V1'


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected exactly one anchor, found {count}')
    return text.replace(old, new, 1)


def harden(text: str) -> str:
    if MARKER in text:
        raise ValueError('runtime state hardening already applied')

    flow_anchor = 'FLOW="$OUT/STAGE3_RUNTIME_FLOW.log"\n'
    helpers = r'''# STAGE3_MULTI_SIGNAL_RUNTIME_V1
LAST_INPUT=none

capture_stage3_diagnostics(){
  local prefix="$1" harness_state="${2:-unknown}" wanted_state="${3:-unknown}"
  local pid process_alive=0 failure_layer
  mkdir -p "$OUT"
  adb logcat -d -v threadtime > "$OUT/${prefix}-logcat.txt" 2>/dev/null || true
  tail -n 250 "$OUT/${prefix}-logcat.txt" > "$OUT/${prefix}-logcat-tail.txt" 2>/dev/null || true
  adb shell dumpsys activity top > "$OUT/${prefix}-top-activity.txt" 2>/dev/null || true
  adb shell dumpsys activity activities > "$OUT/${prefix}-activity.txt" 2>/dev/null || true
  adb shell dumpsys window windows > "$OUT/${prefix}-window.txt" 2>/dev/null || true
  adb exec-out screencap -p > "$OUT/${prefix}-screen.png" 2>/dev/null || true
  pid="$(adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' || true)"
  [ -n "$pid" ] && process_alive=1
  {
    echo "pid=$pid"
    adb shell ps -A 2>/dev/null | grep -F "$PKG" || true
  } > "$OUT/${prefix}-process.txt"
  python3 stage3_harness.py state --json < "$OUT/${prefix}-logcat.txt" > "$OUT/${prefix}-state.json" 2>/dev/null || \
    printf '%s\n' '{"state":"unknown","phase":"unknown","signal":"","line":-1}' > "$OUT/${prefix}-state.json"
  if [ "$process_alive" -eq 1 ]; then
    failure_layer="$(python3 stage3_harness.py classify --process-alive < "$OUT/${prefix}-logcat.txt" 2>/dev/null || echo unknown)"
  else
    failure_layer="$(python3 stage3_harness.py classify < "$OUT/${prefix}-logcat.txt" 2>/dev/null || echo unknown)"
  fi
  {
    echo "failure_layer=$failure_layer"
    echo "harness_state=$harness_state"
    echo "wanted_state=$wanted_state"
    echo "last_input=${LAST_INPUT:-unknown}"
    echo "nss_pid=$pid"
  } > "$OUT/${prefix}-meta.txt"
}
'''
    text = _replace_once(text, flow_anchor, flow_anchor + helpers, 'FLOW helper insertion')

    # Record the last action without changing the proven input coordinates/timing.
    text, n = re.subn(r'press_message_accept\(\)\{', 'press_message_accept(){ LAST_INPUT="press_message_accept";', text, count=1)
    if n != 1:
        raise ValueError('press_message_accept tracking anchor missing')
    text, n = re.subn(r'press_play\(\)\{', 'press_play(){\n  LAST_INPUT="press_play"', text, count=1)
    if n != 1:
        raise ValueError('press_play tracking anchor missing')

    start = text.find('current_state(){')
    end = text.find('wait_state(){', start + 1 if start >= 0 else 0)
    if start < 0 or end < 0 or end <= start:
        raise ValueError('current_state/wait_state boundary not found')

    new_state = r'''current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  local state
  state="$(python3 stage3_harness.py state < "$WORK/state.log" 2>/dev/null || echo unknown)"
  if [ "$state" != unknown ]; then
    echo "$state"
    return 0
  fi
  # Ads are Android Activity overlays rather than Monkey screens/gameplay phases.
  if adb shell dumpsys activity top 2>/dev/null | grep -qiE 'AdActivity|com\.google\.android\.gms\.ads'; then
    echo ad
    return 0
  fi
  echo unknown
}

wait_state(){
  local wanted="$1" timeout_s="${2:-30}" i state safe
  state=unknown
  for i in $(seq 0 "$timeout_s"); do
    fatal_check || return 1
    state="$(current_state)"
    if [[ " $wanted " == *" $state "* ]]; then
      echo "$state"
      return 0
    fi
    sleep 1
  done
  safe="$(printf '%s' "$wanted" | tr ' /' '__')"
  capture_stage3_diagnostics "timeout-$safe" "$state" "$wanted" || true
  capture_log "timeout state $wanted"
  echo unknown
  return 1
}
'''
    text = text[:start] + new_state + text[end + len('wait_state(){'):]
    # The splice above retained the old wait_state body after the opening token;
    # remove it by cutting from the first duplicated old body through dump_save.
    duplicate = text.find('\n  local wanted="$1" timeout_s="${2:-30}" i state', start + len(new_state))
    dump = text.find('\ndump_save(){', start + len(new_state))
    if duplicate >= 0 and dump > duplicate:
        text = text[:duplicate] + text[dump:]

    # MatchReview's weekly/report phase is internal; it needs its own logical state.
    text = text.replace('leaguefixtures|league|matchreview)', 'leaguefixtures|league|matchreview|weeklyreport)')
    text = text.replace('leaguefixtures league gamemenu matchreview message ad',
                        'leaguefixtures league gamemenu matchreview weeklyreport message ad')
    text = text.replace('league matchreview gamemenu message leaguefixtures ad',
                        'league matchreview weeklyreport gamemenu message leaguefixtures ad')

    if 'weeklyreport' not in text:
        raise ValueError('weeklyreport integration postcondition failed')
    if 'capture_stage3_diagnostics' not in text or 'stage3_harness.py state' not in text:
        raise ValueError('runtime hardening postcondition failed')
    return text


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path('stage3_minimal_gate.sh')
    try:
        out = harden(path.read_text(encoding='utf-8'))
    except ValueError as exc:
        raise SystemExit(str(exc))
    path.write_text(out, encoding='utf-8')
    print('STAGE3_RUNTIME_STATE_PATCH=PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
