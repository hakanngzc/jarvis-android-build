#!/usr/bin/env python3
from __future__ import annotations
import hashlib,re,struct,sys,tempfile,zlib,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from dex_inspect import Dex
MATCH='Lcom/newstargames/newstarsoccer/c_TMatch;'
FIXTURE='Lcom/newstargames/newstarsoccer/c_TFixture;'

def unique_index(items,owner,name,kind):
    hits=[i for i,item in enumerate(items) if item[0]==owner and item[1]==name]
    if len(hits)!=1: raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]

def patch_dex(data,dex_name):
    with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f:
        f.write(data); temp=Path(f.name)
    try:
        d=Dex(temp)
        starts=[m for m in (d.class_methods(MATCH) or []) if m[2][1]=='m_StartMatch' and m[4]]
        if not starts:return data,False,None
        if len(starts)!=1: raise ValueError(f'expected one m_StartMatch, found {len(starts)}')
        _,mid,_,acc,code=starts[0]
        if not(acc&0x8):raise ValueError('m_StartMatch is not static')
        fixture_id=unique_index(d.fields,MATCH,'m_fixture','field')
        score1_id=unique_index(d.fields,FIXTURE,'m_score1','field')
        score2_id=unique_index(d.fields,FIXTURE,'m_score2','field')
        over_id=unique_index(d.methods,MATCH,'m_MatchOver','method')
        regs,ins,outs,tries,insns_size,_=d.disasm(code)
        units=[0x0062,fixture_id,0x1112,0x0159,score1_id,0x0112,0x0159,score2_id,0x0071,over_id,0x0000,0x000E]
        if tries:raise ValueError('m_StartMatch has try handlers')
        if regs<2 or insns_size<len(units):raise ValueError(f'unsafe m_StartMatch body regs={regs} units={insns_size}')
        blob=bytearray(data); off=code+16
        repl=units+[0]*(insns_size-len(units))
        struct.pack_into(f'<{insns_size}H',blob,off,*repl)
        blob[12:32]=hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I',blob,8,zlib.adler32(blob[12:])&0xffffffff)
        ev=f'STAGE3 fast-match probe: {dex_name} {MATCH}->m_StartMatch method@{mid} code=0x{code:x} regs={regs} units={insns_size}; selected m_fixture -> 1-0 -> real m_MatchOver method@{over_id}'
        return bytes(blob),True,ev
    finally: temp.unlink(missing_ok=True)

def main():
    if len(sys.argv)!=3:raise SystemExit('usage: patch_stage3_fast_match_probe.py INPUT_APK OUTPUT_APK')
    src,dst=map(Path,sys.argv[1:]); entries=[]; count=0; evidence=[]
    with zipfile.ZipFile(src,'r') as zin:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
                data,changed,ev=patch_dex(data,Path(info.filename).name)
                if changed:count+=1;evidence.append(ev)
            entries.append((info,data))
    if count!=1:raise SystemExit(f'expected exactly one patched DEX, found {count}')
    with zipfile.ZipFile(dst,'w') as zout:
        for info,data in entries:
            zi=zipfile.ZipInfo(info.filename,info.date_time);zi.compress_type=info.compress_type;zi.comment=info.comment;zi.extra=info.extra;zi.internal_attr=info.internal_attr;zi.external_attr=info.external_attr;zi.create_system=info.create_system;zi.flag_bits=info.flag_bits
            zout.writestr(zi,data)
    print('\n'.join(evidence));print(f'Wrote TEST-ONLY Stage3 fast-match probe APK: {dst}')
if __name__=='__main__':main()
