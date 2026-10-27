#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

CAPTURE_OLD = '''  rm -f "$tmp"
  return 1
}

drive_live_chance(){'''

CAPTURE_NEW = '''  rm -f "$tmp"
  local transport_state
  transport_state="$(timeout 4s adb get-state 2>/dev/null || true)"
  if [ "$transport_state" != device ]; then
    printf 'EMULATOR_TRANSPORT_DEAD state=%s\\n' "${transport_state:-unavailable}" \
      | tee -a "$FLOW" > "$OUT/emulator-transport-dead.txt"
    return 4
  fi
  return 1
}

drive_live_chance(){'''

DRIVE_OLD = '''  if ! capture_valid_live_frame "$frame"; then
    echo "cycle $cycle valid live frame unavailable @${elapsed}s; retrying on next match loop" >> "$FLOW"
    sleep 1
    return 0
  fi
'''

DRIVE_NEW = '''  capture_valid_live_frame "$frame" && rc=0 || rc=$?
  if [ "$rc" -eq 4 ]; then
    cp "$OUT/emulator-transport-dead.txt" "$OUT/cycle-$cycle-emulator-transport-dead.txt" 2>/dev/null || true
    echo "cycle $cycle EMULATOR_TRANSPORT_DEAD @${elapsed}s" >> "$FLOW"
    return 4
  fi
  if [ "$rc" -ne 0 ]; then
    echo "cycle $cycle valid live frame unavailable @${elapsed}s; retrying on next match loop" >> "$FLOW"
    sleep 1
    return 0
  fi
'''


def harden(text: str) -> str:
    if 'EMULATOR_TRANSPORT_DEAD' in text:
        return text
    if text.count(CAPTURE_OLD) != 1:
        raise SystemExit(f'expected one live-frame capture tail, found {text.count(CAPTURE_OLD)}')
    text = text.replace(CAPTURE_OLD, CAPTURE_NEW, 1)
    if text.count(DRIVE_OLD) != 1:
        raise SystemExit(f'expected one live-frame unavailable block, found {text.count(DRIVE_OLD)}')
    text = text.replace(DRIVE_OLD, DRIVE_NEW, 1)
    return text


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_stage4_transport_death.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied bounded emulator-transport death classification: {dst}')


if __name__ == '__main__':
    main()
