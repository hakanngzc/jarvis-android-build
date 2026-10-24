#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLUB='Lcom/newstargames/newstarsoccer/c_TClub;'
ID_FIELD=CLUB+'->m_id:I'
STYLE_FIELD=CLUB+'->m_badgestyle:I'
REG=r'[vp]\d+'
BLANK=r'(?:[ \t]*\r?\n)*'
DEFAULT_OVERRIDES={3141:16,3157:17}

# Match the exact stock semantic sequence, while tolerating baksmali's optional
# blank lines and without assuming fixed register numbers.
ANCHOR_RE=re.compile(
    r'(?P<anchor>'
    r'(?P<indent>^[ \t]*)iget (?P<idreg>'+REG+r'), (?P<clubreg>'+REG+r'), '+re.escape(ID_FIELD)+r'\r?\n'+BLANK+
    r'(?P=indent)const/16 (?P<divreg>'+REG+r'), 0xf\r?\n'+BLANK+
    r'(?P=indent)rem-int/2addr (?P=idreg), (?P=divreg)\r?\n'+BLANK+
    r'(?P=indent)iput (?P=idreg), (?P=clubreg), '+re.escape(STYLE_FIELD)+r'\r?\n'
    r')',
    re.M,
)


def _validated_overrides(overrides):
    if overrides is None:
        overrides=DEFAULT_OVERRIDES
    if not isinstance(overrides,dict) or not overrides:
        raise ValueError('badge overrides must be a non-empty mapping')
    normalized={}
    used_styles=set()
    for raw_id,raw_style in overrides.items():
        if isinstance(raw_id,bool) or isinstance(raw_style,bool):
            raise ValueError('club IDs and styles must be integers')
        try:
            club_id=int(raw_id); style=int(raw_style)
        except (TypeError,ValueError):
            raise ValueError('club IDs and styles must be integers')
        if club_id <= 0 or club_id > 0x7fffffff:
            raise ValueError(f'invalid club ID: {club_id}')
        if style <= 15 or style > 0x7fffffff:
            raise ValueError(f'style must be outside reserved stock range 0..15: {style}')
        if club_id in normalized:
            raise ValueError(f'duplicate club ID: {club_id}')
        if style in used_styles:
            raise ValueError(f'duplicate badge style: {style}')
        normalized[club_id]=style; used_styles.add(style)
    return dict(sorted(normalized.items()))


def _const(reg,value):
    if 0 <= value <= 0x7fff:
        return f'const/16 {reg}, {hex(value)}'
    return f'const {reg}, {hex(value)}'


def _override_block(indent,idreg,clubreg,divreg,overrides):
    items=list(overrides.items())
    lines=[f'{indent}iget {idreg}, {clubreg}, {ID_FIELD}']
    for index,(club_id,style) in enumerate(items):
        is_last=index==len(items)-1
        next_label=':nss_reborn_badge_done' if is_last else f':nss_reborn_badge_check_{items[index+1][0]}'
        if index:
            lines.append(f'{indent}:nss_reborn_badge_check_{club_id}')
        lines.append(f'{indent}{_const(divreg,club_id)}')
        lines.append(f'{indent}if-ne {idreg}, {divreg}, {next_label}')
        lines.append(f'{indent}{_const(idreg,style)}')
        lines.append(f'{indent}iput {idreg}, {clubreg}, {STYLE_FIELD}')
        if not is_last:
            lines.append(f'{indent}goto :nss_reborn_badge_done')
            lines.append('')
    lines.extend([
        '',
        f'{indent}:nss_reborn_badge_done',
        # Stock m_CreateClub deliberately reuses the divisor register shortly
        # afterwards as the Clubs.txt field-15 index. Restore that exact scratch
        # register state so targeted style overrides cannot affect later parsing.
        f'{indent}const/16 {divreg}, 0xf',
    ])
    return '\n'.join(lines)+'\n'


def patch_smali_text(text,overrides=None):
    overrides=_validated_overrides(overrides)
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
    override=_override_block(indent,idreg,clubreg,divreg,overrides)
    out=text[:m.end()]+override+text[m.end():]
    report={
        'anchor_count':count,
        'fallback':'m_id % 15',
        'overrides':overrides,
        'override_count':len(overrides),
        'stock_anchor_preserved':anchor in out,
        'inserted_label':'nss_reborn_badge_done',
        'captured_registers':{'id':idreg,'club':clubreg,'divisor':divreg},
        'blank_line_tolerant':True,
        'divisor_register_restored':True,
        'stock_style_range_reserved':'0..15',
    }
    return out,report


def _load_override_file(path):
    payload=json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(payload,dict) and isinstance(payload.get('clubs'),list):
        return {row['club_id']:row['style'] for row in payload['clubs']}
    if isinstance(payload,dict) and isinstance(payload.get('overrides'),dict):
        return payload['overrides']
    if isinstance(payload,dict):
        return payload
    raise ValueError('override JSON must be a mapping or a manifest containing clubs')


def main():
    if len(sys.argv) not in (4,5):
        raise SystemExit(f'usage: {sys.argv[0]} IN.smali OUT.smali REPORT.json [OVERRIDES_OR_MANIFEST.json]')
    src,dst,report=map(Path,sys.argv[1:4])
    overrides=_load_override_file(sys.argv[4]) if len(sys.argv)==5 else None
    text=src.read_text(encoding='utf-8')
    out,meta=patch_smali_text(text,overrides=overrides)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(out,encoding='utf-8')
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(meta,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    pairs=','.join(f'{club}:{style}' for club,style in meta['overrides'].items())
    print(f"CLUB_BADGE_OVERRIDE_PATCH=PASS fallback=id%15 overrides={pairs} registers="+json.dumps(meta['captured_registers'],sort_keys=True)+' divisor_restored=true')

if __name__=='__main__': main()
