#!/usr/bin/env python3
import re
import sys
from pathlib import Path

METHOD_RE = re.compile(r'(?ms)^\.method[^\n]*\bm_CreateClub\([^\n]*\n(?P<body>.*?)^\.end method\s*$')
STOCK_RE = re.compile(
    r'(?m)^(?P<i>[ \t]*)iget (?P<style>v\d+), (?P<obj>[vp]\d+), '
    r'Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I\s*\n\s*'
    r'const/16 (?P<div>v\d+), 0xf\s*\n\s*'
    r'rem-int/2addr (?P=style), (?P=div)\s*\n\s*'
    r'iput (?P=style), (?P=obj), '
    r'Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I'
)


def patch_text(text: str) -> str:
    if 'reborn_badge_done' in text or 'reborn_check_3163' in text:
        raise ValueError('Stage6 badge-style patch already present')
    methods = list(METHOD_RE.finditer(text))
    if len(methods) != 1:
        raise ValueError(f'expected exactly one m_CreateClub method, found {len(methods)}')
    method = methods[0]
    body = method.group('body')
    sites = list(STOCK_RE.finditer(body))
    if len(sites) != 1:
        raise ValueError(f'expected exactly one stock badge-style site, found {len(sites)}')

    site = sites[0]
    i = site.group('i')
    style = site.group('style')
    obj = site.group('obj')
    div = site.group('div')
    # Re-use the same two compact registers as the stock modulo block. The
    # stock fallback is committed before the target checks, so every other club
    # keeps its original club_id % 15 value. No new v16+ register is introduced.
    replacement = (
        f'{i}iget {style}, {obj}, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I\n\n'
        f'{i}const/16 {div}, 0xf\n\n'
        f'{i}rem-int/2addr {style}, {div}\n\n'
        f'{i}iput {style}, {obj}, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I\n\n'
        f'{i}iget {style}, {obj}, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I\n\n'
        f'{i}const/16 {div}, 0xc45\n\n'
        f'{i}if-ne {style}, {div}, :reborn_check_3163\n\n'
        f'{i}const/16 {style}, 0x10\n\n'
        f'{i}iput {style}, {obj}, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I\n\n'
        f'{i}goto :reborn_badge_done\n\n'
        f'{i}:reborn_check_3163\n'
        f'{i}iget {style}, {obj}, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I\n\n'
        f'{i}const/16 {div}, 0xc5b\n\n'
        f'{i}if-ne {style}, {div}, :reborn_badge_done\n\n'
        f'{i}const/16 {style}, 0x11\n\n'
        f'{i}iput {style}, {obj}, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I\n\n'
        f'{i}:reborn_badge_done'
    )
    body = body[:site.start()] + replacement + body[site.end():]
    return text[:method.start('body')] + body + text[method.end('body'):]


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(f'usage: {sys.argv[0]} IN.smali OUT.smali')
    src, dst = map(Path, sys.argv[1:])
    dst.write_text(patch_text(src.read_text(encoding='utf-8')), encoding='utf-8')
    print('STAGE6_CLUB_STYLE_PATCH=PASS ids=3141:16,3163:17 fallback=club_id%15')


if __name__ == '__main__':
    main()
