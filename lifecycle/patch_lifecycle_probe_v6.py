#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v5 import ACTIVITY_ONSTOP_REPLACEMENT, patch_script as v5_patch_script

COMBINED_DRIVER_REPLACEMENT = r'''python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe-stock.apk"
python3 lifecycle/dump_graphics_lifecycle_code.py \
  "$WORK/base-career-probe-stock.apk" \
  --out "$OUT/LIFECYCLE_GRAPHICS_CODE.json" \
  | tee "$OUT/LIFECYCLE_GRAPHICS_CODE.txt"
python3 lifecycle/patch_activity_super_lifecycle.py \
  "$WORK/base-career-probe-stock.apk" "$WORK/base-career-probe-super.apk" \
  --evidence "$OUT/LIFECYCLE_ACTIVITY_SUPER_PATCH.json" \
  | tee "$OUT/LIFECYCLE_ACTIVITY_SUPER_PATCH.txt"
grep -q 'VERDICT=LIFECYCLE_ACTIVITY_SUPER_PATCH_APPLIED' "$OUT/LIFECYCLE_ACTIVITY_SUPER_PATCH.txt"
python3 lifecycle/patch_gl_resume_race.py \
  "$WORK/base-career-probe-super.apk" "$WORK/base-career-probe.apk" \
  --evidence "$OUT/LIFECYCLE_GL_RESUME_PATCH.json" \
  | tee "$OUT/LIFECYCLE_GL_RESUME_PATCH.txt"
grep -q 'VERDICT=LIFECYCLE_GL_RESUME_PATCH_APPLIED' "$OUT/LIFECYCLE_GL_RESUME_PATCH.txt"'''


def combine_activity_and_resume(text: str) -> str:
    count = text.count(ACTIVITY_ONSTOP_REPLACEMENT)
    if count != 1:
        raise ValueError(f'expected one v5 activity-super candidate block, found {count}')
    return text.replace(ACTIVITY_ONSTOP_REPLACEMENT, COMBINED_DRIVER_REPLACEMENT, 1)


def patch_script(text: str) -> str:
    generated = v5_patch_script(text)
    return combine_activity_and_resume(generated)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v6.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v6: {src} -> {dst}')


if __name__ == '__main__':
    main()
