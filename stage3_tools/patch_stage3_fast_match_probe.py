#!/usr/bin/env python3
from __future__ import annotations
import hashlib, re, struct, sys, tempfile, zlib, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from dex_inspect import Dex

MATCH='Lcom/newstargames/newstarsoccer/c_TMatch;'
FIXTURE='Lcom/newstargames/newstarsoccer/c_TFixture;'
GSUTILITY='Lcom/newstargames/newstarsoccer/bb_GSMatchUtility;'

def unique_index(items,owner,name,kind):
    hits=[i for i,item in enumerate(items) if item[0]==owner and item[1]==name]
    if len(hits)!=1: raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]

def proto_signature(d, method_id):
    _owner,_name,proto_id=d.methods[method_id]
    shorty_idx,return_type_idx,params_off=struct.unpack_from('<III',d.b,d.proto_off+12*proto_id)
    params=[]
    if params_off:
        count=struct.unpack_from('<I',d.b,params_off)[0]
        params=[d.types[struct.unpack_from('<H',d.b,params_off+4+2*i)[0]] for i in range(count)]
    return d.types[return_type_idx],params,d.strings[shorty_idx]

def build_probe_units(fixture_id,score1_id,score2_id,over_id,matchstate_id,half_id,matchmin_id,gs_over_id):
    # m_StartMatch()I TEST-ONLY fast-forward:
    # - keep the real selected fixture
    # - force a deterministic 1-0
    # - reproduce the stock full-time boundary used by m_DoHalfEnds:
    #   minute=90, half=2, real m_MatchOver(true), then state=5 when it succeeds
    # - run the stock GS match-over hook and return the real MatchOver result.
    return [
        0x0062,fixture_id,          # sget-object v0, m_fixture
        0x1112,                     # const/4 v1, #1
        0x0159,score1_id,           # iput v1, v0, m_score1
        0x0112,                     # const/4 v1, #0
        0x0159,score2_id,           # iput v1, v0, m_score2
        0x0113,0x005a,              # const/16 v1, #90
        0x0167,matchmin_id,         # sput v1, m_matchmin
        0x2112,                     # const/4 v1, #2
        0x0167,half_id,             # sput v1, m_half
        0x1112,                     # const/4 v1, #1 (true)
        0x1071,over_id,0x0001,      # invoke-static {v1}, m_MatchOver(Z)I
        0x000a,                     # move-result v0
        0x0038,0x0008,              # if-eqz v0, return v0
        0x5112,                     # const/4 v1, #5
        0x0167,matchstate_id,       # sput v1, m_matchstate
        0x0071,gs_over_id,0x0000,   # invoke-static {}, g_GSOnMatchOver()V
        0x000f,                     # return v0
    ]

def patch_dex(data,dex_name):
    with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f: f.write(data); tmp=f.name
    try:
        d=Dex(tmp); starts=[m for m in (d.class_methods(MATCH) or []) if m[2][1]=='m_StartMatch' and m[4]]
        if not starts: return data,False,None
        if len(starts)!=1: raise ValueError(f'expected one m_StartMatch, found {len(starts)}')
        _kind,method_id,_mt,access,code=starts[0]
        if not (access & 0x8): raise ValueError('m_StartMatch is not static')
        start_ret,start_params,start_shorty=proto_signature(d,method_id)
        if (start_ret,start_params)!=('I',[]):
            raise ValueError(f'unexpected m_StartMatch proto: shorty={start_shorty} return={start_ret} params={start_params}')
        fixture_id=unique_index(d.fields,MATCH,'m_fixture','field')
        score1_id=unique_index(d.fields,FIXTURE,'m_score1','field')
        score2_id=unique_index(d.fields,FIXTURE,'m_score2','field')
        matchstate_id=unique_index(d.fields,MATCH,'m_matchstate','field')
        half_id=unique_index(d.fields,MATCH,'m_half','field')
        matchmin_id=unique_index(d.fields,MATCH,'m_matchmin','field')
        over_id=unique_index(d.methods,MATCH,'m_MatchOver','method')
        gs_over_id=unique_index(d.methods,GSUTILITY,'g_GSOnMatchOver','method')
        over_ret,over_params,over_shorty=proto_signature(d,over_id)
        if (over_ret,over_params)!=('I',['Z']):
            raise ValueError(f'unexpected m_MatchOver proto: shorty={over_shorty} return={over_ret} params={over_params}')
        gs_ret,gs_params,gs_shorty=proto_signature(d,gs_over_id)
        if (gs_ret,gs_params)!=('V',[]):
            raise ValueError(f'unexpected g_GSOnMatchOver proto: shorty={gs_shorty} return={gs_ret} params={gs_params}')
        regs,ins,outs,tries,size,_=d.disasm(code)
        if tries: raise ValueError('m_StartMatch has try handlers')
        if regs<2: raise ValueError('m_StartMatch needs 2 registers')
        if outs<1: raise ValueError('m_StartMatch needs at least one outgoing argument register')
        units=build_probe_units(
            fixture_id,score1_id,score2_id,over_id,
            matchstate_id,half_id,matchmin_id,gs_over_id,
        )
        if size<len(units): raise ValueError(f'm_StartMatch too small: {size}')
        blob=bytearray(data); off=code+16
        replacement=units+[0]*(size-len(units)); struct.pack_into(f'<{size}H',blob,off,*replacement)
        blob[12:32]=hashlib.sha1(blob[32:]).digest(); struct.pack_into('<I',blob,8,zlib.adler32(blob[12:]) & 0xffffffff)
        ev=(f'STAGE3 fast-match probe: {dex_name} m_StartMatch()I method@{method_id} code=0x{code:x}; '
            f'selected m_fixture -> 1-0 -> minute90/half2 -> real m_MatchOver(true)I method@{over_id} '
            f'-> stock full-time state5 -> g_GSOnMatchOver method@{gs_over_id} -> return result')
        return bytes(blob),True,ev
    finally: Path(tmp).unlink(missing_ok=True)

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: patch_stage3_fast_match_probe.py INPUT_APK OUTPUT_APK')
    src,dst=map(Path,sys.argv[1:]); entries=[]; patched=0; evidence=[]
    with zipfile.ZipFile(src) as zin:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
                data,changed,ev=patch_dex(data,Path(info.filename).name)
                if changed: patched+=1; evidence.append(ev)
            entries.append((info,data))
    if patched!=1: raise SystemExit(f'expected exactly one patched DEX, found {patched}')
    with zipfile.ZipFile(dst,'w') as zout:
        for info,data in entries:
            zi=zipfile.ZipInfo(info.filename,info.date_time); zi.compress_type=info.compress_type; zi.comment=info.comment; zi.extra=info.extra; zi.internal_attr=info.internal_attr; zi.external_attr=info.external_attr; zi.create_system=info.create_system; zi.flag_bits=info.flag_bits; zout.writestr(zi,data)
    print('\n'.join(evidence)); print(f'Wrote TEST-ONLY Stage3 fast-match probe APK: {dst}')
if __name__=='__main__': main()
