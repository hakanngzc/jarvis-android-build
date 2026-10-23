#!/usr/bin/env python3
import re
import sys
from pathlib import Path

DECL_3141 = 'Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)'
DECL_3163 = 'Img:(RebornBadge3163,NewGUI/RebornBadges/3163.png)'
SEL_RE = re.compile(
    r'(?m)^(?P<sel_indent>[ \t]*)Selector\(MatchColours,(?P<style>BadgeStyle[12])\)[ \t]*\n'
    r'(?P<brace_indent>[ \t]*)\{'
)


def _indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(' \t'))


def _matching_brace(text: str, open_pos: int) -> int:
    depth = 0
    for i in range(open_pos, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError('unterminated selector block')


def _design15_block(block: str):
    lines = block.splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if 'Draw:(MapShieldDesign15' in line]
    if len(hits) != 1:
        raise ValueError(f'expected exactly one Design15 draw in selector, found {len(hits)}')
    i = hits[0]
    indent = _indent_width(lines[i])
    parts = [lines[i]]
    j = i + 1
    while j < len(lines):
        line = lines[j]
        if not line.strip() or _indent_width(line) <= indent:
            break
        parts.append(line)
        j += 1
    return ''.join(parts), lines[i][:indent]


def patch_text(text: str) -> str:
    if 'RebornBadge3141' in text or 'RebornBadge3163' in text or 'STAGE6_REAL_LOGO_OVERLAY' in text:
        raise ValueError('Stage6 shield UI patch already present')
    selectors = list(SEL_RE.finditer(text))
    design15_count = text.count('Draw:(MapShieldDesign15')
    if not selectors or design15_count != len(selectors):
        raise ValueError(f'expected one Design15 child per badge selector, selectors={len(selectors)} design15={design15_count}')

    out = text
    for m in reversed(selectors):
        open_pos = out.find('{', m.start(), m.end() + 1)
        if open_pos < 0:
            raise ValueError('selector opening brace not found')
        close_pos = _matching_brace(out, open_pos)
        block = out[open_pos + 1:close_pos]
        design15, child_indent = _design15_block(block)
        style = m.group('style')
        brace_indent = m.group('brace_indent')
        sel_indent = m.group('sel_indent')

        # Extend the stock tinted selector to indices 16/17 with NO-OP children.
        # This keeps procedural styles 0..15 intact without tinting the raw logos.
        close_line_start = out.rfind('\n', open_pos, close_pos) + 1
        noops = child_indent + 'Rect:(0,0,0,0)\n' + child_indent + 'Rect:(0,0,0,0)\n'
        out = out[:close_line_start] + noops + out[close_line_start:]
        close_pos += len(noops)

        # A second selector is outside the ColReadout tint scope. Children 0..15
        # are empty; 16/17 draw the full-colour raw badge with the exact local
        # Design15 transform/modifiers for this shield variant.
        empty_children = ''.join(child_indent + 'Rect:(0,0,0,0)\n' for _ in range(16))
        custom3141 = design15.replace('MapShieldDesign15', 'RebornBadge3141', 1)
        custom3163 = design15.replace('MapShieldDesign15', 'RebornBadge3163', 1)
        overlay = (
            '\n' + sel_indent + f'// STAGE6_REAL_LOGO_OVERLAY {style}\n'
            + sel_indent + f'Selector(MatchColours,{style})\n'
            + brace_indent + '{\n'
            + empty_children
            + custom3141
            + custom3163
            + brace_indent + '}\n'
        )
        insert_at = close_pos + 1
        out = out[:insert_at] + overlay + out[insert_at:]

    return DECL_3141 + '\n' + DECL_3163 + '\n' + out


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f'usage: {sys.argv[0]} IN.uih OUT.uih')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(patch_text(src.read_text(encoding='utf-8')), encoding='utf-8')
    print('STAGE6_SHIELD_UI_PATCH=PASS styles=16,17 mode=untinted-overlay')


if __name__ == '__main__':
    main()
