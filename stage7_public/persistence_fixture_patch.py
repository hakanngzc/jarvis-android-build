#!/usr/bin/env python3
import re

PLAYER='Lcom/newstargames/newstarsoccer/c_TPlayer;'
BB='Lcom/newstargames/newstarsoccer/bb_;'


def _method_block(text,name,expected_return='I'):
    pat=re.compile(rf'(?ms)^\.method[^\n]*\b{re.escape(name)}\(\)(\S+)\n.*?^\.end method\s*$')
    hits=list(pat.finditer(text))
    if len(hits)!=1:
        raise ValueError(f'expected exactly one {name}() method, found {len(hits)}')
    ret=hits[0].group(1)
    if ret!=expected_return:
        raise ValueError(f'{name} return type mismatch: expected {expected_return}, got {ret}')
    return hits[0],ret


def _expand_frame(block,extra,param_count):
    locals_hits=list(re.finditer(r'(?m)^(\s*)\.locals\s+(\d+)\s*$',block))
    regs_hits=list(re.finditer(r'(?m)^(\s*)\.registers\s+(\d+)\s*$',block))
    if len(locals_hits)+len(regs_hits)!=1:
        raise ValueError(f'expected exactly one .locals/.registers directive, found locals={len(locals_hits)} registers={len(regs_hits)}')
    if locals_hits:
        m=locals_hits[0]; old_locals=int(m.group(2)); old_registers=None
        directive='locals'; new_locals=old_locals+extra; new_registers=None
        # Under .locals, explicit vN at/above the old local boundary aliases a
        # parameter register. Expanding locals would move that parameter.
        for r in re.finditer(r'\bv(\d+)\b',block):
            if int(r.group(1))>=old_locals:
                raise ValueError(f'explicit parameter register {r.group(0)} prevents .locals expansion')
        repl=f'{m.group(1)}.locals {new_locals}'
        scratch_base=old_locals
    else:
        m=regs_hits[0]; old_registers=int(m.group(2))
        if old_registers < param_count:
            raise ValueError(f'.registers {old_registers} smaller than parameter count {param_count}')
        old_locals=old_registers-param_count
        new_locals=old_locals+extra; new_registers=old_registers+extra
        directive='registers'
        # With .registers, the final param_count registers are parameters. The
        # patch is safe only when stock code addresses those through pN aliases.
        for r in re.finditer(r'\bv(\d+)\b',block):
            if int(r.group(1))>=old_locals:
                raise ValueError(f'explicit parameter register {r.group(0)} prevents .registers expansion')
        repl=f'{m.group(1)}.registers {new_registers}'
        scratch_base=old_locals
    patched=block[:m.start()]+repl+block[m.end():]
    meta={'directive':directive,'old_locals':old_locals,'new_locals':new_locals,'scratch_base':scratch_base}
    if old_registers is not None:
        meta.update({'old_registers':old_registers,'new_registers':new_registers})
    return patched,meta


def _inject_after_frame(block,addition):
    m=re.search(r'(?m)^\s*\.(?:locals|registers)\s+\d+\s*$',block)
    if not m: raise ValueError('.locals/.registers missing after expansion')
    return block[:m.end()]+addition+block[m.end():]


def patch_mutator_text(text):
    marker='STAGE7_TEST_MUTATOR_BEGIN'
    if marker in text: raise ValueError('mutator already present')
    m,ret=_method_block(text,'p_SaveCareer','I'); block=m.group(0)
    block,frame=_expand_frame(block,3,param_count=1)
    a,b,c=frame['scratch_base'],frame['scratch_base']+1,frame['scratch_base']+2
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
    patched=_inject_after_frame(block,add)
    out=text[:m.start()]+patched+text[m.end():]
    meta={'method':'p_SaveCareer','return_type':ret,**frame,'scratch':[f'v{a}',f'v{b}',f'v{c}']}
    return out,meta


def patch_verifier_text(text):
    marker='STAGE7_TEST_VERIFY_RESAVE_BEGIN'
    if marker in text: raise ValueError('verifier already present')
    m,ret=_method_block(text,'m_LoadCareer','I'); block=m.group(0)
    returns=list(re.finditer(r'(?m)^(\s*)return\s+(v\d+|p\d+)\s*$',block))
    if len(returns)!=1:
        raise ValueError(f'expected exactly one int return in m_LoadCareer, found {len(returns)}')
    return_reg=returns[0].group(2)
    block,frame=_expand_frame(block,1,param_count=0)
    reg=frame['scratch_base']
    if reg<16:
        invoke=f'invoke-virtual {{v{reg}}}, {PLAYER}->p_SaveCareer()I'
    else:
        invoke=f'invoke-virtual/range {{v{reg} .. v{reg}}}, {PLAYER}->p_SaveCareer()I'
    add=f'''    # {marker}
    sget-object v{reg}, {BB}->g_player:{PLAYER}
    {invoke}
    move-result v{reg}
    # STAGE7_TEST_VERIFY_RESAVE_END
'''
    r=list(re.finditer(r'(?m)^(\s*)return\s+'+re.escape(return_reg)+r'\s*$',block))
    if len(r)!=1: raise ValueError('unique original return lost after frame expansion')
    pos=r[0].start()
    block=block[:pos]+add+block[pos:]
    out=text[:m.start()]+block+text[m.end():]
    return out,{'method':'m_LoadCareer','return_type':ret,'return_register':return_reg,**frame,'scratch':f'v{reg}'}
