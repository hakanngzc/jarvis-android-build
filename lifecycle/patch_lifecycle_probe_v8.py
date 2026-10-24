#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v7 import patch_script as v7_patch_script

SLOT_FINDER_START = '''find_slot0_target(){\npython3 - "$1" "$2" <<'PY'\n'''
SLOT_FINDER_END = '''\nPY\n}\n\ncurrent_state(){'''
SLOT_FINDER_REPLACEMENT = '''find_slot0_target(){\n  python3 lifecycle/slot_target_geometry.py "$1" "$2"\n}\n\ncurrent_state(){'''


def patch_slot_finder(text: str) -> str:
    if text.count(SLOT_FINDER_START) != 1 or text.count(SLOT_FINDER_END) != 1:
        raise ValueError('expected exactly one v7 SaveSlot finder block')
    start = text.index(SLOT_FINDER_START)
    end = text.index(SLOT_FINDER_END, start)
    old_block = text[start : end + len(SLOT_FINDER_END)]
    if "palette=[(246,233,210),(217,229,227),(255,249,237)]" not in old_block:
        raise ValueError('v7 SaveSlot finder fingerprint changed')
    if "print('slot0_target',x,y,'bands',groups)" not in old_block:
        raise ValueError('v7 SaveSlot finder output marker changed')
    return text[:start] + SLOT_FINDER_REPLACEMENT + text[end + len(SLOT_FINDER_END) :]


def patch_script(text: str) -> str:
    generated = v7_patch_script(text)
    return patch_slot_finder(generated)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v8.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v8: {src} -> {dst}')


if __name__ == '__main__':
    main()
