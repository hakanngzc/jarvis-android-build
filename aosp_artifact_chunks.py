#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

CHUNK_SIZE = 220 * 1024 * 1024


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('source', type=Path)
    p.add_argument('outdir', type=Path)
    args = p.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    parts: list[Path] = []
    with args.source.open('rb') as src:
        index = 0
        while True:
            data = src.read(CHUNK_SIZE)
            if not data:
                break
            part = args.outdir / f'aosp29.part-{index:02d}'
            part.write_bytes(data)
            parts.append(part)
            index += 1

    manifest = args.outdir / 'SHA256SUMS.txt'
    lines = [f'{sha256(args.source)}  {args.source.name}']
    lines.extend(f'{sha256(part)}  {part.name}' for part in parts)
    manifest.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'parts={len(parts)}')
    for part in parts:
        print(f'{part.name} {part.stat().st_size}')
    print(manifest.read_text(encoding='utf-8'), end='')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
