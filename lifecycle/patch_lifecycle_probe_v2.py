#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe import patch_script as base_patch_script

PID_ANCHOR = '''pid_one(){ adb shell pidof "$PKG" 2>/dev/null | tr -d '\\r' | awk '{print $1}'; }'''
PID_REPLACEMENT = '''pid_one(){ (adb shell pidof "$PKG" 2>/dev/null || true) | tr -d '\\r' | awk '{print $1}'; }'''

HIDDEN_ANCHOR = '''  hidden="$(pid_one)"; [ "$before" = "$hidden" ] || { echo "process died in background ($tag): $before -> $hidden"; return 1; }'''
HIDDEN_REPLACEMENT = '''  hidden="$(pid_one)"
  if [ "$before" != "$hidden" ]; then
    adb shell dumpsys activity processes > "$OUT/lifecycle-${tag}-background-processes.txt" 2>/dev/null || true
    adb logcat -d -v threadtime > "$OUT/lifecycle-${tag}-background-logcat.txt" 2>/dev/null || true
    lifecycle_record "${tag}_background_process_survived" FAIL
    echo "process died in background ($tag): $before -> ${hidden:-<none>}"
    return 1
  fi
  lifecycle_record "${tag}_background_process_survived" PASS'''

AFTER_ANCHOR = '''  after="$(pid_one)"; [ "$before" = "$after" ] || { echo "process changed after foreground ($tag): $before -> $after"; return 1; }'''
AFTER_REPLACEMENT = '''  after="$(pid_one)"
  if [ "$before" != "$after" ]; then
    adb shell dumpsys activity processes > "$OUT/lifecycle-${tag}-foreground-processes.txt" 2>/dev/null || true
    adb logcat -d -v threadtime > "$OUT/lifecycle-${tag}-foreground-logcat.txt" 2>/dev/null || true
    lifecycle_record "${tag}_foreground_same_pid" FAIL
    echo "process changed after foreground ($tag): $before -> ${after:-<none>}"
    return 1
  fi
  lifecycle_record "${tag}_foreground_same_pid" PASS'''


def one_replace(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f'expected one {label} anchor, found {count}')
    return text.replace(old, new, 1)


def harden_generated_script(text: str) -> str:
    text = one_replace(text, PID_ANCHOR, PID_REPLACEMENT, 'pid_one')
    text = one_replace(text, HIDDEN_ANCHOR, HIDDEN_REPLACEMENT, 'background pid check')
    text = one_replace(text, AFTER_ANCHOR, AFTER_REPLACEMENT, 'foreground pid check')
    return text


def patch_script(text: str) -> str:
    return harden_generated_script(base_patch_script(text))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v2.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v2: {src} -> {dst}')


if __name__ == '__main__':
    main()
