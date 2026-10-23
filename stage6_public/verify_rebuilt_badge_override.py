#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLUB='Lcom/newstargames/newstarsoccer/c_TClub;'
ID_FIELD=CLUB+'->m_id:I'
STYLE_FIELD=CLUB+'->m_badgestyle:I'


def _find(text, needle, start=0, label=None):
    pos=text.find(needle,start)
    if pos < 0:
        raise ValueError('rebuilt override verification missing: '+(label or needle))
    return pos


def verify_rebuilt_override(text, report):
    regs=report.get('captured_registers') or {}
    i=regs.get('id'); c=regs.get('club'); d=regs.get('divisor')
    if not all((i,c,d)):
        raise ValueError('captured registers missing from override report')
    if not report.get('divisor_register_restored'):
        raise ValueError('override report does not attest divisor restoration')

    # Stock fallback must remain before the new override branches.
    p_c45=_find(text,f'const/16 {d}, 0xc45')
    prefix=text[:p_c45]
    p_iget=_find(prefix,f'iget {i}, {c}, {ID_FIELD}')
    p_fallback_const=_find(prefix,f'const/16 {d}, 0xf',p_iget)
    p_rem=_find(prefix,f'rem-int/2addr {i}, {d}',p_fallback_const)
    p_fallback_write=_find(prefix,f'iput {i}, {c}, {STYLE_FIELD}',p_rem)
    if not (p_iget < p_fallback_const < p_rem < p_fallback_write < p_c45):
        raise ValueError('stock id%15 fallback order changed')

    # Club 3141: compare ID, write style 16, then jump over the 3157 branch.
    p_if1=_find(text,f'if-ne {i}, {d},',p_c45,'3141 conditional branch')
    p_s16=_find(text,f'const/16 {i}, 0x10',p_if1)
    p_w16=_find(text,f'iput {i}, {c}, {STYLE_FIELD}',p_s16)
    p_goto=_find(text,'goto ',p_w16,'3141 done jump')

    # Club 3157: second compare and style 17 write.
    p_c55=_find(text,f'const/16 {d}, 0xc55',p_goto)
    p_if2=_find(text,f'if-ne {i}, {d},',p_c55,'3157 conditional branch')
    p_s17=_find(text,f'const/16 {i}, 0x11',p_if2)
    p_w17=_find(text,f'iput {i}, {c}, {STYLE_FIELD}',p_s17)
    if not (p_c45 < p_if1 < p_s16 < p_w16 < p_goto < p_c55 < p_if2 < p_s17 < p_w17):
        raise ValueError('badge override branch order changed')

    # The divisor register is later reused by stock code as Clubs.txt field
    # index 15. It must be restored to 0xf after both override branches and
    # before its next use as an array index.
    p_restore=_find(text,f'const/16 {d}, 0xf',p_w17,'divisor restore')
    index_use=re.search(r'^\s*aget-object\s+\S+,\s*\S+,\s*'+re.escape(d)+r'\s*$',text[p_w17:],re.M)
    if index_use is not None:
        p_index=p_w17+index_use.start()
        if p_restore > p_index:
            raise ValueError('divisor restore occurs after next array-index use')
    else:
        p_index=-1

    write_count=text.count(f'iput {i}, {c}, {STYLE_FIELD}')
    if write_count != 3:
        raise ValueError(f'expected exactly 3 badge style writes after rebuild, got {write_count}')

    return {
        'fallback_present':True,
        'club3141_branch_present':True,
        'club3157_branch_present':True,
        'divisor_restore_before_next_field_read':True,
        'badge_style_write_count':write_count,
        'captured_registers':{'id':i,'club':c,'divisor':d},
        'positions':{
            'fallback_write':p_fallback_write,'club3141_const':p_c45,
            'club3157_const':p_c55,'divisor_restore':p_restore,'next_divisor_index_use':p_index,
        },
    }


def main():
    if len(sys.argv)!=3:
        raise SystemExit(f'usage: {sys.argv[0]} REBUILT_METHOD.smali OVERRIDE_REPORT.json')
    text=Path(sys.argv[1]).read_text(encoding='utf-8')
    report=json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    result=verify_rebuilt_override(text,report)
    print('REBUILT_BADGE_OVERRIDE_VERIFY=PASS '+json.dumps(result,sort_keys=True))


if __name__=='__main__': main()
