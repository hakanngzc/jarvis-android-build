#!/usr/bin/env python3
import re

PLAYER='Lcom/newstargames/newstarsoccer/c_TPlayer;'
BB='Lcom/newstargames/newstarsoccer/bb_;'


def _method_block(text,name):
    pat=re.compile(rf'(?ms)^\.method[^\n]*\b{re.escape(name)}\(\)V\n.*?^\.end method\s*$')
    hits=list(pat.finditer(text))
    if len(hits)!=1:
        raise ValueError(f'expected exactly one {name}()V method, found {len(hits)}')
    return hits[0]


def _expand_locals(block,extra):
    hits=list(re.finditer(r'(?m)^(\s*)\.locals\s+(\d+)\s*$',block))
    if len(hits)!=1:
        raise ValueError(f'expected exactly one .locals directive, found {len(hits)}')
    m=hits[0]; old=int(m.group(2)); new=old+extra
    # Increasing .locals is safe only when baksmali used p-register aliases for
    # parameters. Explicit vN references at/above old locals would change meaning.
    for r in re.finditer(r'\bv(\d+)\b',block):
        if int(r.group(1))>=old:
            raise ValueError(f'explicit parameter register {r.group(0)} prevents .locals expansion')
    repl=f'{m.group(1)}.locals {new}'
    return block[:m.start()]+repl+block[m.end():],old,new,m.start()+len(repl)


def _inject_after_locals(block,addition):
    m=re.search(r'(?m)^\s*\.locals\s+\d+\s*$',block)
    if not m: raise ValueError('.locals missing after expansion')
    return block[:m.end()]+addition+block[m.end():]


def patch_mutator_text(text):
    marker='STAGE7_TEST_MUTATOR_BEGIN'
    if marker in text: raise ValueError('mutator already present')
    m=_method_block(text,'p_SaveCareer'); block=m.group(0)
    block,base,new,_=_expand_locals(block,3)
    a,b,c=base,base+1,base+2
    add=f'''

    # {marker}
    const/16 v{a}, 0x10e1
    iput v{a}, p0, {PLAYER}->m_bank:I
    const/16 v{a}, 0x141
    iput v{a}, p0, {PLAYER}->m_wage:I
    const/16 v{a}, 0x4d
    iput v{a}, p0, {PLAYER}->m_goalbonus:I
    const/16 v{a}, 0x37
    iput v{a}, p0, {PLAYER}->m_assistbonus:I
    const/16 v{a}, 0x3039
    iput v{a}, p0, {PLAYER}->m_lasttransferdate:I
    const/16 v{a}, 0x3038
    iput v{a}, p0, {PLAYER}->m_lastnegotiations:I
    const v{a}, 0x42750000
    iput v{a}, p0, {PLAYER}->m_relationboss:F
    const v{a}, 0x427a0000
    iput v{a}, p0, {PLAYER}->m_relationteam:F
    const v{a}, 0x427f0000
    iput v{a}, p0, {PLAYER}->m_relationfans:F
    const v{a}, 0x42810000
    iput v{a}, p0, {PLAYER}->m_relationfriends:F
    const v{a}, 0x42828000
    iput v{a}, p0, {PLAYER}->m_relationgirlfriend:F
    const v{a}, 0x42850000
    iput v{a}, p0, {PLAYER}->m_relationsponsors:F
    const v{a}, 0x418a0000
    iput v{a}, p0, {PLAYER}->m_lastspendtimefriends:F
    const v{a}, 0x41940000
    iput v{a}, p0, {PLAYER}->m_lastspendtimegirlfriend:F
    const/4 v{a}, 0x7
    iput v{a}, p0, {PLAYER}->m_spenttime:I
    const/4 v{a}, 0x3
    iput v{a}, p0, {PLAYER}->m_gambling:I
    const/4 v{b}, 0x0
    const/16 v{c}, 0x47
    iget-object v{a}, p0, {PLAYER}->m_technique:[I
    aput v{c}, v{a}, v{b}
    const/16 v{c}, 0x48
    iget-object v{a}, p0, {PLAYER}->m_pace:[I
    aput v{c}, v{a}, v{b}
    const/16 v{c}, 0x49
    iget-object v{a}, p0, {PLAYER}->m_vision:[I
    aput v{c}, v{a}, v{b}
    const/16 v{c}, 0x4a
    iget-object v{a}, p0, {PLAYER}->m_setpieces:[I
    aput v{c}, v{a}, v{b}
    const/16 v{c}, 0x4b
    iget-object v{a}, p0, {PLAYER}->m_power:[I
    aput v{c}, v{a}, v{b}
    const/4 v{a}, 0x5
    iput v{a}, p0, {PLAYER}->m_donetraining:I
    const/4 v{a}, 0x6
    iput v{a}, p0, {PLAYER}->m_trainingattempts:I
    # STAGE7_TEST_MUTATOR_END
'''
    patched=_inject_after_locals(block,add)
    out=text[:m.start()]+patched+text[m.end():]
    return out,{'method':'p_SaveCareer','old_locals':base,'new_locals':new}


def patch_verifier_text(text):
    marker='STAGE7_TEST_VERIFY_RESAVE_BEGIN'
    if marker in text: raise ValueError('verifier already present')
    m=_method_block(text,'m_LoadCareer'); block=m.group(0)
    if block.count('return-void')!=1:
        raise ValueError(f'expected exactly one return-void in m_LoadCareer, found {block.count("return-void")}')
    block,base,new,_=_expand_locals(block,1)
    reg=base
    if reg<16:
        invoke=f'invoke-virtual {{v{reg}}}, {PLAYER}->p_SaveCareer()V'
    else:
        invoke=f'invoke-virtual/range {{v{reg} .. v{reg}}}, {PLAYER}->p_SaveCareer()V'
    add=f'''    # {marker}
    sget-object v{reg}, {BB}->g_player:{PLAYER}
    {invoke}
    # STAGE7_TEST_VERIFY_RESAVE_END
    return-void'''
    block=block.replace('    return-void',add,1)
    out=text[:m.start()]+block+text[m.end():]
    return out,{'method':'m_LoadCareer','old_locals':base,'new_locals':new,'scratch':f'v{reg}'}
