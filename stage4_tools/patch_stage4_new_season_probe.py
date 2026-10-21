#!/usr/bin/env python3
from __future__ import annotations
import hashlib,re,struct,sys,tempfile,zlib,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1] / 'stage3_tools'))
from dex_inspect import Dex

UTILITY='Lcom/newstargames/newstarsoccer/bb_GSPlayerUtility;'
BB='Lcom/newstargames/newstarsoccer/bb_;'
PLAYER='Lcom/newstargames/newstarsoccer/c_TPlayer;'
TARGET='g_GSPlayerPlayMatches'

def unique_index(items,owner,name,kind):
    hits=[i for i,item in enumerate(items) if item[0]==owner and item[1]==name]
    if len(hits)!=1: raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]

def proto_signature(d,mid):
    _owner,_name,proto_id=d.methods[mid]
    shorty_idx,ret_idx,params_off=struct.unpack_from('<III',d.b,d.proto_off+12*proto_id)
    params=[]
    if params_off:
        count=struct.unpack_from('<I',d.b,params_off)[0]
        params=[d.types[struct.unpack_from('<H',d.b,params_off+4+2*i)[0]] for i in range(count)]
    return d.types[ret_idx],params,d.strings[shorty_idx]

def build_probe_units(player_field,date_field,sdate_field,season_apps_field,new_season_mid):
    # TEST-ONLY GameMenu Play trigger:
    # player.m_date.m_sdate = 365 (year 2, week 1/day 1 boundary)
    # player.m_seasonApps = 7 (sentinel proving stock p_ResetSeasonStats ran)
    # player.p_NewSeason(0)
    return [
        0x0062,player_field,
        0x0254,date_field,
        0x0313,0x016d,
        0x2359,sdate_field,
        0x7112,
        0x0159,season_apps_field,
        0x0112,
        0x206e,new_season_mid,0x0010,
        0x000a,
        0x000e,
    ]

def patch_dex(data,dex_name):
    with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f: f.write(data); tmp=f.name
    try:
        d=Dex(tmp)
        methods=[m for m in (d.class_methods(UTILITY) or []) if m[2][1]==TARGET and m[4]]
        if not methods: return data,False,None
        if len(methods)!=1: raise ValueError(f'expected one {TARGET}, found {len(methods)}')
        _kind,mid,_mt,access,code=methods[0]
        if not (access & 0x8): raise ValueError(f'{TARGET} is not static')
        ret,params,shorty=proto_signature(d,mid)
        if (ret,params)!=('V',[]): raise ValueError(f'unexpected {TARGET} proto: {shorty} {ret} {params}')
        new_mid=unique_index(d.methods,PLAYER,'p_NewSeason','method')
        nret,nparams,nshorty=proto_signature(d,new_mid)
        if (nret,nparams)!=('I',['I']): raise ValueError(f'unexpected p_NewSeason proto: {nshorty} {nret} {nparams}')
        player_field=unique_index(d.fields,BB,'g_player','field')
        date_field=unique_index(d.fields,PLAYER,'m_date','field')
        sdate_field=unique_index(d.fields,'Lcom/newstargames/newstarsoccer/c_TMyDate;','m_sdate','field')
        season_field=unique_index(d.fields,PLAYER,'m_seasonApps','field')
        regs,ins,outs,tries,size,_=d.disasm(code)
        if tries: raise ValueError(f'{TARGET} has try handlers')
        if regs<4 or outs<2: raise ValueError(f'{TARGET} lacks registers/outs: regs={regs} outs={outs}')
        units=build_probe_units(player_field,date_field,sdate_field,season_field,new_mid)
        if size<len(units): raise ValueError(f'{TARGET} too small: {size} < {len(units)}')
        blob=bytearray(data); off=code+16
        struct.pack_into(f'<{size}H',blob,off,*(units+[0]*(size-len(units))))
        blob[12:32]=hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I',blob,8,zlib.adler32(blob[12:]) & 0xffffffff)
        ev=(f'STAGE4 new-season probe: {dex_name} {TARGET}()V method@{mid} code=0x{code:x}; '
            f'seed season boundary sdate=365 + m_seasonApps=7 -> real p_NewSeason(0) method@{new_mid}; all staged season writers remain stock')
        return bytes(blob),True,ev
    finally: Path(tmp).unlink(missing_ok=True)

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: patch_stage4_new_season_probe.py INPUT_APK OUTPUT_APK')
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
    print('\n'.join(evidence)); print(f'Wrote TEST-ONLY Stage4 new-season probe APK: {dst}')
if __name__=='__main__': main()
