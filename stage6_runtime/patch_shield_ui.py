#!/usr/bin/env python3
import re
import sys
from pathlib import Path

DECL_3141 = 'Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)'
DECL_3163 = 'Img:(RebornBadge3163,NewGUI/RebornBadges/3163.png)'


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(' \t'))


def patch_text(text: str) -> str:
    if 'RebornBadge3141' in text or 'RebornBadge3163' in text:
        raise ValueError('Stage6 shield UI patch already present')
    selector_count = text.count('Selector(MatchColours,BadgeStyle1)') + text.count('Selector(MatchColours,BadgeStyle2)')
    design15_count = text.count('Draw:(MapShieldDesign15')
    if selector_count <= 0 or design15_count != selector_count:
        raise ValueError(f'expected one Design15 child per badge selector, selectors={selector_count} design15={design15_count}')

    lines = text.splitlines(keepends=True)
    out = []
    patched = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'Draw:(MapShieldDesign15' not in line:
            out.append(line)
            i += 1
            continue
        indent = _indent_width(line)
        block = [line]
        j = i + 1
        while j < len(lines):
            nxt = lines[j]
            if not nxt.strip():
                break
            if _indent_width(nxt) <= indent:
                break
            block.append(nxt)
            j += 1
        out.extend(block)
        raw = ''.join(block)
        out.append(raw.replace('MapShieldDesign15', 'RebornBadge3141', 1))
        out.append(raw.replace('MapShieldDesign15', 'RebornBadge3163', 1))
        patched += 1
        i = j
    if patched != selector_count:
        raise ValueError(f'patched selector count mismatch: patched={patched} selectors={selector_count}')
    return DECL_3141 + '\n' + DECL_3163 + '\n' + ''.join(out)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f'usage: {sys.argv[0]} IN.uih OUT.uih')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(patch_text(src.read_text(encoding='utf-8')), encoding='utf-8')
    print('STAGE6_SHIELD_UI_PATCH=PASS styles=16,17')


if __name__ == '__main__':
    main()
