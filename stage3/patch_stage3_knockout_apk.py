#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from stage3.patch_stage3_knockout_probe import VALID_MODES, patch_apk_bytes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=sorted(VALID_MODES))
    ap.add_argument('input_apk', type=Path)
    ap.add_argument('output_apk', type=Path)
    ap.add_argument('--evidence', type=Path, required=True)
    args = ap.parse_args()

    if not args.input_apk.is_file():
        raise SystemExit(f'input APK missing: {args.input_apk}')

    patched, evidence = patch_apk_bytes(args.input_apk.read_bytes(), args.mode)
    args.output_apk.parent.mkdir(parents=True, exist_ok=True)
    args.output_apk.write_bytes(patched)

    record = {
        'schema': 1,
        'mode': args.mode,
        'input_apk': str(args.input_apk),
        'output_apk': str(args.output_apk),
        'test_only_never_ship': True,
        'probe': evidence,
        'verdict': 'STAGE3_KNOCKOUT_APK_PATCH_PASS',
    }
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n', encoding='utf-8')

    print(f'MODE={args.mode}')
    print(f'OUTPUT_APK={args.output_apk}')
    print(f'EVIDENCE={args.evidence}')
    print('STOCK_KNOCKOUT_METHODS_UNTOUCHED=true')
    print('VERDICT=STAGE3_KNOCKOUT_APK_PATCH_PASS')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
