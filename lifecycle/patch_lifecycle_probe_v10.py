#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v9 import CONTEXT_SURVIVAL_DRIVER_REPLACEMENT, patch_script as v9_patch_script

CONTEXT_SURVIVAL_RENDER_DRIVER_REPLACEMENT = r'''python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe-stock.apk"
python3 lifecycle/dump_graphics_lifecycle_code.py \
  "$WORK/base-career-probe-stock.apk" \
  --out "$OUT/LIFECYCLE_GRAPHICS_CODE.json" \
  | tee "$OUT/LIFECYCLE_GRAPHICS_CODE.txt"
python3 lifecycle/patch_gl_context_survival_render.py \
  "$WORK/base-career-probe-stock.apk" "$WORK/base-career-probe.apk" \
  --evidence "$OUT/LIFECYCLE_GL_CONTEXT_SURVIVAL_RENDER_PATCH.json" \
  | tee "$OUT/LIFECYCLE_GL_CONTEXT_SURVIVAL_RENDER_PATCH.txt"
grep -q 'VERDICT=LIFECYCLE_GL_CONTEXT_SURVIVAL_RENDER_PATCH_APPLIED' "$OUT/LIFECYCLE_GL_CONTEXT_SURVIVAL_RENDER_PATCH.txt"'''


def replace_v9_candidate(text: str) -> str:
    count = text.count(CONTEXT_SURVIVAL_DRIVER_REPLACEMENT)
    if count != 1:
        raise ValueError(f'expected one v9 context-survival candidate block, found {count}')
    return text.replace(CONTEXT_SURVIVAL_DRIVER_REPLACEMENT, CONTEXT_SURVIVAL_RENDER_DRIVER_REPLACEMENT, 1)


def patch_script(text: str) -> str:
    return replace_v9_candidate(v9_patch_script(text))


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v10.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v10: {src} -> {dst}')


if __name__ == '__main__':
    main()
