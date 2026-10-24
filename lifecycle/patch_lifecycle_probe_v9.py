#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v6 import COMBINED_DRIVER_REPLACEMENT
from patch_lifecycle_probe_v8 import patch_script as v8_patch_script

CONTEXT_SURVIVAL_DRIVER_REPLACEMENT = r'''python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe-stock.apk"
python3 lifecycle/dump_graphics_lifecycle_code.py \
  "$WORK/base-career-probe-stock.apk" \
  --out "$OUT/LIFECYCLE_GRAPHICS_CODE.json" \
  | tee "$OUT/LIFECYCLE_GRAPHICS_CODE.txt"
python3 lifecycle/patch_gl_context_survival.py \
  "$WORK/base-career-probe-stock.apk" "$WORK/base-career-probe.apk" \
  --evidence "$OUT/LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH.json" \
  | tee "$OUT/LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH.txt"
grep -q 'VERDICT=LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH_APPLIED' "$OUT/LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH.txt"'''


def replace_failed_gl_candidate(text: str) -> str:
    count = text.count(COMBINED_DRIVER_REPLACEMENT)
    if count != 1:
        raise ValueError(f'expected one v8 combined super+resume candidate block, found {count}')
    return text.replace(COMBINED_DRIVER_REPLACEMENT, CONTEXT_SURVIVAL_DRIVER_REPLACEMENT, 1)


def patch_script(text: str) -> str:
    generated = v8_patch_script(text)
    return replace_failed_gl_candidate(generated)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v9.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v9: {src} -> {dst}')


if __name__ == '__main__':
    main()
