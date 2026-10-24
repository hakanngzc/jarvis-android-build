#!/usr/bin/env python3
from __future__ import annotations
import re, struct, sys, tempfile, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'stage3_tools'))
from dex_inspect import Dex

TARGETS = {
    'Lcom/newstargames/newstarsoccer/c_TScreen_Contract;': ('m_ButtonAccept','m_ButtonReject','m_SetUpScreen'),
    'Lcom/newstargames/newstarsoccer/c_TContractOffer;': ('p_SignContract','m_','p_'),
    'Lcom/newstargames/newstarsoccer/c_TScreen_DesiredTransfer;': ('m_','p_'),
    'Lcom/newstargames/newstarsoccer/c_TScreen_Retirement;': ('m_ButtonPlay','m_SetUpScreen','m_'),
    'Lcom/newstargames/newstarsoccer/c_TPlayer;': ('p_Retire','p_QuickSave','p_SaveCareer','p_PlayToDate'),
    'Lcom/newstargames/newstarsoccer/bb_;': ('g_player',''),
}

def proto(d: Dex, mid: int):
    _owner, _name, proto_id = d.methods[mid]
    shorty_idx, ret_idx, params_off = struct.unpack_from('<III', d.b, d.proto_off + 12 * proto_id)
    params=[]
    if params_off:
        n=struct.unpack_from('<I', d.b, params_off)[0]
        params=[d.types[struct.unpack_from('<H', d.b, params_off+4+2*i)[0]] for i in range(n)]
    return d.types[ret_idx], params, d.strings[shorty_idx]

def dump_apk(apk: Path):
    with zipfile.ZipFile(apk) as z:
        dex_entries=[n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', Path(n).name)]
        with tempfile.TemporaryDirectory() as td:
            for dex_name in dex_entries:
                p=Path(td)/Path(dex_name).name
                p.write_bytes(z.read(dex_name))
                d=Dex(p)
                for desc, needles in TARGETS.items():
                    methods=d.class_methods(desc) or []
                    fields=[(i,f) for i,f in enumerate(d.fields) if f[0]==desc]
                    if not methods and not fields:
                        continue
                    print(f'===== {dex_name} {desc} =====')
                    for i,f in fields:
                        print('FIELD',i,f)
                    for kind,mid,m,acc,code in methods:
                        if needles and not any(n and n in m[1] for n in needles):
                            continue
                        ret,params,shorty=proto(d,mid)
                        print(f'\nMETHOD {kind} mid={mid} name={m[1]} access={hex(acc)} code={hex(code)} proto={shorty} ret={ret} params={params}')
                        if not code:
                            continue
                        regs,ins,outs,tries,sz,items=d.disasm(code)
                        print(f'HEADER regs={regs} ins={ins} outs={outs} tries={tries} units={sz}')
                        for off,name,args,raw in items:
                            print(f'{off:05x}: {raw:<30} {name:<26} {args}')

def main():
    if len(sys.argv)!=2:
        raise SystemExit('usage: inspect_residual_targets.py BASE_APK')
    dump_apk(Path(sys.argv[1]))

if __name__=='__main__':
    main()
