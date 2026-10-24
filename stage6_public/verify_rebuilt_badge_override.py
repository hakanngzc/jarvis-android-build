#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLUB='Lcom/newstargames/newstarsoccer/c_TClub;'
ID_FIELD=CLUB+'->m_id:I'
STYLE_FIELD=CLUB+'->m_badgestyle:I'
DEFAULT_OVERRIDES={3141:16,3157:17}


def _find(text, needle, start=0, label=None):
    pos=text.find(needle,start)
    if pos < 0:
        raise ValueError('rebuilt override verification missing: '+(label or needle))
    return pos


def _const_candidates(reg,value):
    h=hex(value)
    return (f'const/16 {reg}, {h}',f'const {reg}, {h}')


def _find_const(text,reg,value,start=0,label=None):
    hits=[]
    for needle in _const_candidates(reg,value):
        p=text.find(needle,start)
        if p>=0: hits.append((p,needle))
    if not hits:
        raise ValueError('rebuilt override verification missing: '+(label or f'{reg}={value}'))
    return min(hits)[0]


def _overrides(report):
    raw=report.get('overrides') or DEFAULT_OVERRIDES
    try:
        items=sorted((int(k),int(v)) for k,v in raw.items())
    except Exception as exc:
        raise ValueError('invalid override map in report') from exc
    if not items: raise ValueError('empty override map in report')
    return items


def verify_rebuilt_override(text, report):
    regs=report.get('captured_registers') or {}
    i=regs.get('id'); c=regs.get('club'); d=regs.get('divisor')
    if not all((i,c,d)):
        raise ValueError('captured registers missing from override report')
    if not report.get('divisor_register_restored'):
        raise ValueError('override report does not attest divisor restoration')
    overrides=_overrides(report)

    # Stock fallback must remain before the first override comparison.
    first_id,first_style=overrides[0]
    p_first=_find_const(text,d,first_id,label=f'club {first_id} ID constant')
    prefix=text[:p_first]
    p_iget=_find(prefix,f'iget {i}, {c}, {ID_FIELD}')
    p_fallback_const=_find(prefix,f'const/16 {d}, 0xf',p_iget)
    p_rem=_find(prefix,f'rem-int/2addr {i}, {d}',p_fallback_const)
    p_fallback_write=_find(prefix,f'iput {i}, {c}, {STYLE_FIELD}',p_rem)
    if not (p_iget < p_fallback_const < p_rem < p_fallback_write < p_first):
        raise ValueError('stock id%15 fallback order changed')

    cursor=p_first
    positions=[]
    last_write=-1
    for club_id,style in overrides:
        p_id=_find_const(text,d,club_id,cursor,label=f'club {club_id} ID constant')
        branch=re.search(r'^\s*if-ne\s+'+re.escape(i)+r',\s*'+re.escape(d)+r',\s*:\S+',text[p_id:],re.M)
        if branch is None:
            raise ValueError(f'missing conditional branch for club {club_id}')
        p_if=p_id+branch.start()
        p_style=_find_const(text,i,style,p_if,label=f'club {club_id} style {style}')
        p_write=_find(text,f'iput {i}, {c}, {STYLE_FIELD}',p_style,f'club {club_id} badge write')
        if not (p_id <= p_if < p_style < p_write):
            raise ValueError(f'override order changed for club {club_id}')
        positions.append({'club_id':club_id,'style':style,'id_const':p_id,'branch':p_if,'style_const':p_style,'write':p_write})
        cursor=p_write+1; last_write=p_write

    p_restore=_find(text,f'const/16 {d}, 0xf',last_write,'divisor restore')
    index_use=re.search(r'^\s*aget-object\s+\S+,\s*\S+,\s*'+re.escape(d)+r'\s*$',text[last_write:],re.M)
    if index_use is not None:
        p_index=last_write+index_use.start()
        if p_restore > p_index:
            raise ValueError('divisor restore occurs after next array-index use')
    else:
        p_index=-1

    write_count=text.count(f'iput {i}, {c}, {STYLE_FIELD}')
    expected_writes=1+len(overrides)
    if write_count != expected_writes:
        raise ValueError(f'expected exactly {expected_writes} badge style writes after rebuild, got {write_count}')

    result={
        'fallback_present':True,
        'override_count':len(overrides),
        'overrides':dict(overrides),
        'divisor_restore_before_next_field_read':True,
        'badge_style_write_count':write_count,
        'captured_registers':{'id':i,'club':c,'divisor':d},
        'positions':positions,
        'divisor_restore':p_restore,
        'next_divisor_index_use':p_index,
    }
    # Backward-compatible proof fields used by the historical two-ID tests.
    result['club3141_branch_present']=3141 in dict(overrides)
    result['club3157_branch_present']=3157 in dict(overrides)
    return result


def main():
    if len(sys.argv)!=3:
        raise SystemExit(f'usage: {sys.argv[0]} REBUILT_METHOD.smali OVERRIDE_REPORT.json')
    text=Path(sys.argv[1]).read_text(encoding='utf-8')
    report=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    result=verify_rebuilt_override(text,report)
    print('REBUILT_BADGE_OVERRIDE_VERIFY=PASS '+json.dumps(result,sort_keys=True))


if __name__=='__main__': main()
