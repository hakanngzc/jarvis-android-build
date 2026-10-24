#!/usr/bin/env python3
import sys
from pathlib import Path

from patch_lifecycle_probe_v4 import GL_DRIVER_REPLACEMENT, patch_script as v4_patch_script

ACTIVITY_ONSTOP_REPLACEMENT = r'''python3 tools/patch_trial_skip_for_persistence_test.py "$WORK/base-cloud-probe.apk" "$WORK/base-career-probe-stock.apk"
python3 lifecycle/patch_activity_super_lifecycle.py \
  "$WORK/base-career-probe-stock.apk" "$WORK/base-career-probe.apk" \
  --evidence "$OUT/LIFECYCLE_ACTIVITY_ONSTOP_PATCH.json" \
  | tee "$OUT/LIFECYCLE_ACTIVITY_ONSTOP_PATCH.txt"
grep -q 'VERDICT=LIFECYCLE_ACTIVITY_ONSTOP_PATCH_APPLIED' "$OUT/LIFECYCLE_ACTIVITY_ONSTOP_PATCH.txt"'''


def replace_resume_candidate(text: str) -> str:
    count = text.count(GL_DRIVER_REPLACEMENT)
    if count != 1:
        raise ValueError(f'expected one v4 resume-order candidate block, found {count}')
    return text.replace(GL_DRIVER_REPLACEMENT, ACTIVITY_ONSTOP_REPLACEMENT, 1)


def patch_script(text: str) -> str:
    generated = v4_patch_script(text)
    return replace_resume_candidate(generated)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_lifecycle_probe_v5.py INPUT_SH OUTPUT_SH')
    src, dst = map(Path, sys.argv[1:])
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(patch_script(src.read_text(encoding='utf-8')), encoding='utf-8')
    dst.chmod(0o755)
    print(f'patched lifecycle probe v5: {src} -> {dst}')


if __name__ == '__main__':
    main()
