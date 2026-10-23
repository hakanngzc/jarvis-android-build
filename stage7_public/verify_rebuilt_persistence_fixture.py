#!/usr/bin/env python3
import json,re,sys
from pathlib import Path

P='Lcom/newstargames/newstarsoccer/c_TPlayer;'
B='Lcom/newstargames/newstarsoccer/bb_;'


def _frame(block,meta):
    if meta.get('directive')=='registers':
        m=re.search(r'(?m)^\s*\.registers\s+(\d+)\s*$',block)
        if not m or int(m.group(1))!=int(meta['new_registers']):
            raise ValueError(f'rebuilt .registers mismatch: expected {meta.get("new_registers")}')
    elif meta.get('directive')=='locals':
        m=re.search(r'(?m)^\s*\.locals\s+(\d+)\s*$',block)
        if not m or int(m.group(1))!=int(meta['new_locals']):
            raise ValueError(f'rebuilt .locals mismatch: expected {meta.get("new_locals")}')
    else:
        raise ValueError(f'unsupported frame directive: {meta.get("directive")}')


def _const_iput(block,field,literal):
    pat=rf'(?ms)\bconst(?:/4|/16)?\s+(v\d+),\s*{re.escape(literal)}(?:\s+#[^\n]*)?\s*\n\s*iput\s+\1,\s*p0,\s*{re.escape(P)}->{re.escape(field)}:[IF]'
    if not re.search(pat,block):
        raise ValueError(f'missing rebuilt value/write pair: {field}={literal}')


def _skill_write(block,field,literal):
    # The injected sequence loads the value, obtains the target skill array and
    # writes index 0. Register numbers may be reformatted by baksmali, so bind
    # them through regex backreferences rather than hard-coding v7/v8/v9.
    pat=(rf'(?ms)\bconst/16\s+(v\d+),\s*{re.escape(literal)}.*?'
         rf'iget-object\s+(v\d+),\s*p0,\s*{re.escape(P)}->{re.escape(field)}:\[I.*?'
         rf'aput\s+\1,\s+\2,\s+(v\d+)')
    m=re.search(pat,block)
    if not m:
        raise ValueError(f'missing rebuilt skill array write: {field}={literal}')
    idx=m.group(3)
    prefix=block[:m.start()]
    if not re.search(rf'(?m)^\s*const/4\s+{re.escape(idx)},\s*0x0\s*$',prefix):
        raise ValueError(f'skill array index register is not proven zero: {field} index={idx}')
    return int(literal,16)


def verify_mutator(block,meta):
    if not re.search(r'(?m)^\.method[^\n]*\bp_SaveCareer\(\)I\s*$',block):
        raise ValueError('rebuilt p_SaveCareer()I method missing')
    _frame(block,meta)
    pairs={
        'm_bank':'0x10e1','m_wage':'0x141','m_goalbonus':'0x4d','m_assistbonus':'0x37',
        'm_lasttransferdate':'0x3039','m_lastnegotiations':'0x3038',
        'm_relationboss':'0x42750000','m_relationsponsors':'0x42850000',
        'm_spenttime':'0x7','m_gambling':'0x3','m_donetraining':'0x5',
    }
    for field,literal in pairs.items(): _const_iput(block,field,literal)
    skills=[
        _skill_write(block,'m_technique','0x47'),
        _skill_write(block,'m_pace','0x48'),
        _skill_write(block,'m_vision','0x49'),
        _skill_write(block,'m_setpieces','0x4a'),
        _skill_write(block,'m_power','0x4b'),
    ]
    return {'pass':True,'mode':'mutator','bank':'4321','wage':'321','skills':skills,'frame':meta['directive']}


def verify_verifier(block,meta):
    if not re.search(r'(?m)^\.method[^\n]*\bm_LoadCareer\(\)I\s*$',block):
        raise ValueError('rebuilt m_LoadCareer()I method missing')
    _frame(block,meta)
    scratch=meta['scratch']; ret=meta['return_register']
    sget=rf'sget-object\s+{re.escape(scratch)},\s*{re.escape(B)}->g_player:{re.escape(P)}'
    inv=(rf'invoke-virtual(?:/range)?\s+\{{[^\n}}]*{re.escape(scratch)}[^\n}}]*\}},\s*'
         rf'{re.escape(P)}->p_SaveCareer\(\)I')
    move=rf'move-result\s+{re.escape(scratch)}'
    ms=re.search(sget,block); mi=re.search(inv,block); mm=re.search(move,block)
    if not (ms and mi and mm and ms.start()<mi.start()<mm.start()):
        raise ValueError('rebuilt verifier resave sequence missing or reordered')
    returns=list(re.finditer(r'(?m)^\s*return\s+(v\d+|p\d+)\s*$',block))
    if len(returns)!=1 or returns[0].group(1)!=ret:
        raise ValueError(f'original return register not preserved: expected {ret}, got {[m.group(1) for m in returns]}')
    if mm.start()>returns[0].start():
        raise ValueError('resave sequence occurs after original return')
    return {'pass':True,'mode':'verifier','return_register':ret,'scratch':scratch,'frame':meta['directive']}


def _extract_method(text,mode):
    name='p_SaveCareer' if mode=='mutator' else 'm_LoadCareer'
    m=re.search(r'(?ms)^\.method[^\n]*\b'+re.escape(name)+r'\(\)I\n.*?^\.end method\s*$',text)
    if not m: raise ValueError(f'rebuilt target method missing: {name}')
    return m.group(0)


def main():
    if len(sys.argv)!=6:
        raise SystemExit(f'usage: {sys.argv[0]} REBUILT_c_TPlayer.smali MODE META.json METHOD_OUT.txt REPORT.json')
    src,mode,meta_path,method_out,report_path=sys.argv[1:]
    if mode not in ('mutator','verifier'): raise SystemExit('mode must be mutator or verifier')
    text=Path(src).read_text(encoding='utf-8'); meta=json.load(open(meta_path,encoding='utf-8'))
    block=_extract_method(text,mode); Path(method_out).write_text(block+'\n',encoding='utf-8')
    report=verify_mutator(block,meta) if mode=='mutator' else verify_verifier(block,meta)
    Path(report_path).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'STAGE7_REBUILT_VERIFY=PASS mode={mode} method={meta["method"]} return=I semantic=verified')

if __name__=='__main__': main()
