#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

START_RE = re.compile(r'''(?ms)^start_game\(\)\{.*?^\}\nopen_slot0\(\)\{''')

NEW = r'''start_game(){
  local tag="$1" start_attempt rendered ready_i bytes startup_crashed

  stash_startup_fatal(){
    local fatal="$OUT/runtime-fatal-logcat.txt"
    if [ -s "$fatal" ]; then
      cp "$fatal" "$OUT/${tag}-startup-attempt-${start_attempt}-fatal.txt" 2>/dev/null || true
      rm -f "$fatal"
    fi
  }

  for start_attempt in 1 2; do
    echo "start_game $tag attempt $start_attempt/2"
    startup_crashed=0
    adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
    clear_log
    rm -f "$OUT/runtime-fatal-logcat.txt"
    adb shell am start -n "$PKG/.MonkeyGame" >/dev/null

    if ! wait_log 'Create Screen:[[:space:]]*mainmenu|SETTING ACTIVE:[[:space:]]*mainmenu|SetActive:[[:space:]]*mainmenu' 60 "${tag}-mainmenu-attempt-${start_attempt}"; then
      adb logcat -d -v threadtime > "$OUT/${tag}-mainmenu-attempt-${start_attempt}-timeout.txt" 2>/dev/null || true
      shot "${tag}-mainmenu-attempt-${start_attempt}-timeout"
      if [ -s "$OUT/runtime-fatal-logcat.txt" ]; then
        startup_crashed=1
        stash_startup_fatal
        echo "start_game $tag attempt $start_attempt crashed before stable MainMenu; controlled process restart"
      else
        echo "start_game $tag attempt $start_attempt did not reach Monkey MainMenu; controlled process restart"
      fi
      sleep 3
      continue
    fi

    rendered=0
    for ready_i in $(seq 1 45); do
      if ! fatal_check; then
        startup_crashed=1
        stash_startup_fatal
        break
      fi
      adb exec-out screencap -p > "$WORK/render-probe.png" 2>/dev/null || true
      bytes="$(wc -c < "$WORK/render-probe.png" 2>/dev/null || echo 0)"
      if [ "${bytes:-0}" -gt 30000 ]; then
        cp "$WORK/render-probe.png" "$OUT/${tag}-render-ready.png" 2>/dev/null || true
        echo "Rendered frame ready after ${ready_i}s (${bytes} bytes)"
        rendered=1
        break
      fi
      sleep 1
    done

    if [ "$rendered" -eq 1 ] && test -n "$(adb shell pidof "$PKG" | tr -d '\r' || true)"; then
      capture_log "$tag mainmenu"
      return 0
    fi

    cp "$WORK/render-probe.png" "$OUT/${tag}-render-attempt-${start_attempt}-timeout.png" 2>/dev/null || true
    adb logcat -d -v threadtime > "$OUT/${tag}-render-attempt-${start_attempt}-timeout.txt" 2>/dev/null || true
    if [ "$startup_crashed" -eq 1 ]; then
      echo "start_game $tag attempt $start_attempt crashed before stable MainMenu; controlled process restart"
    else
      echo "start_game $tag attempt $start_attempt reached MainMenu log but not a stable rendered process; controlled retry"
    fi
    sleep 3
  done

  echo "start_game $tag failed after 2 controlled attempts"
  return 1
}
open_slot0(){'''


def harden(text: str) -> str:
    if 'render-probe.png' not in text:
        raise SystemExit('runtime start retry hardener requires the rendered-frame prepared gate')
    matches = list(START_RE.finditer(text))
    if len(matches) != 1:
        raise SystemExit(f'expected one prepared start_game block, found {len(matches)}')
    return START_RE.sub(lambda _m: NEW, text, count=1)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: prepare_runtime_start_retry.py INPUT_GATE OUTPUT_GATE')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(harden(src.read_text(encoding='utf-8')), encoding='utf-8')
    print(f'Applied bounded process-start retry hardening: {dst}')


if __name__ == '__main__':
    main()
