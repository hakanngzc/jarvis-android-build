#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLUB='Lcom/newstargames/newstarsoccer/c_TClub;'
ID_FIELD=CLUB+'->m_id:I'
STYLE_FIELD=CLUB+'->m_badgestyle:I'
REG=r'[vp]\d+'

# Match the exact stock semantic sequence, but do not assume baksmali chose the
# same register numbers as our synthetic unit fixture.
ANCHOR_RE=re.compile(
    r'(?P<anchor>'
    r'(?P<indent>^[ \t]*)iget (?P<idreg>'+REG+r'), (?P<clubreg>'+REG+r'), '+re.escape(ID_FIELD)+r'\r?\n'
    r'(?P=indent)const/16 (?P<divreg>'+REG+r'), 0xf\r?\n'
    r'(?P=indent)rem-int/2addr (?P=idreg), (?P=divreg)\r?\n'
    r'(?P=indent)iput (?P=idreg), (?P=clubreg), '+re.escape(STYLE_FIELD)+r'\r?\n'
    r')',
    re.M,
)


def patch_smali_text(text):
    matches=list(ANCHOR_RE.finditer(text))
    count=len(matches)
    if count!=1:
        raise ValueError(f'stock badge-style anchor expected once, got {count}')
    if ':nss_reborn_badge_done' in text:
        raise ValueError('badge override already present')

    m=matches[0]
    indent=m.group('indent')
    idreg=m.group('idreg')
    clubreg=m.group('clubreg')
    divreg=m.group('divreg')
    anchor=m.group('anchor')
    override=(
        f'{indent}iget {idreg}, {clubreg}, {ID_FIELD}\n'
        f'{indent}const/16 {divreg}, 0xc45\n'
        f'{indent}if-ne {idreg}, {divreg}, :nss_reborn_badge_check_3157\n'
        f'{indent}const/16 {idreg}, 0x10\n'
        f'{indent}iput {idreg}, {clubreg}, {STYLE_FIELD}\n'
        f'{indent}goto :nss_reborn_badge_done\n\n'
        f'{indent}:nss_reborn_badge_check_3157\n'
        f'{indent}const/16 {divreg}, 0xc55\n'
        f'{indent}if-ne {idreg}, {divreg}, :nss_reborn_badge_done\n'
        f'{indent}const/16 {idreg}, 0x11\n'
        f'{indent}iput {idreg}, {clubreg}, {STYLE_FIELD}\n\n'
        f'{indent}:nss_reborn_badge_done\n'
    )
    out=text[:m.end()]+override+text[m.end():]
    report={
        'anchor_count':count,
        'fallback':'m_id % 15',
        'overrides':{'3141':16,'3157':17},
        'stock_anchor_preserved':anchor in out,
        'inserted_label':'nss_reborn_badge_done',
        'captured_registers':{'id':idreg,'club':clubreg,'divisor':divreg},
    }
    return out,report


def main():
    if len(sys.argv)!=4:
        raise SystemExit(f'usage: {sys.argv[0]} IN.smali OUT.smali REPORT.json')
    src,dst,report=map(Path,sys.argv[1:])
    text=src.read_text(encoding='utf-8')
    out,meta=patch_smali_text(text)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(out,encoding='utf-8')
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print('CLUB_BADGE_OVERRIDE_PATCH=PASS fallback=id%15 overrides=3141:16,3157:17 registers='+json.dumps(meta['captured_registers'],sort_keys=True))

if __name__=='__main__': main()
