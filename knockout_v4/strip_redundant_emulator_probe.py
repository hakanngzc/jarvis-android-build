#!/usr/bin/env python3
"""Remove the redundant nested emulator version probe from the V2 wrapper."""
from __future__ import annotations

BLOCK = '''# The repository contract pins this exact Android Emulator build.\nemulator -version 2>&1 | tee "$RUNNER_TEMP/nss-stage3-emulator-version.txt"\ngrep -q 'build_id 16428233' "$RUNNER_TEMP/nss-stage3-emulator-version.txt"\n\n'''


def strip_redundant_emulator_probe(text: str) -> str:
    count = text.count(BLOCK)
    if count != 1:
        raise ValueError(f'expected exactly one redundant emulator probe block, found {count}')
    return text.replace(BLOCK, '', 1)
