#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, struct, sys, tempfile, zlib, zipfile
from pathlib import Path

def _dex_class():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'stage3_tools'))
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'stage3_tools'))
    from dex_inspect import Dex
    return Dex

UTILITY='Lcom/newstargames/newstarsoccer/bb_GSPlayerUtility;'
BB='Lcom/newstargames/newstarsoccer/bb_;'
PLAYER='Lcom/newstargames/newstarsoccer/c_TPlayer;'
TARGET='g_GSPlayerPlayMatches'

SENTINELS={
    'bank':54321,
    'lastnegotiations':2121,
    'items0':9876,
    'sponsors0':8765,
    'relationsponsors':95.25,
    'relationboss':73.25,
    'energy':88.5,
    'technique0':99,
    'deplete_technique':2468,
    'iapAgent1':1357,
}

def unique_index(items,owner,name,kind):
    hits=[i for i,item in enumerate(items) if item[0]==owner and item[1]==name]
    if len(hits)!=1:
        raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]

def proto_signature(d,mid):
    _owner,_name,proto_id=d.methods[mid]
    shorty_idx,ret_idx,params_off=struct.unpack_from('<III',d.b,d.proto_off+12*proto_id)
    params=[]
    if params_off:
        count=struct.unpack_from('<I',d.b,params_off)[0]
        params=[d.types[struct.unpack_from('<H',d.b,params_off+4+2*i)[0]] for i in range(count)]
    return d.types[ret_idx],params,d.strings[shorty_idx]

def _const32(reg,value):
    value &= 0xffffffff
    return [0x14 | (reg<<8), value & 0xffff, value >> 16]

def _const16(reg,value):
    return [0x13 | (reg<<8), value & 0xffff]

def _float_const(reg,value):
    bits=struct.unpack('<I',struct.pack('<f',float(value)))[0]
    return _const32(reg,bits)

def _iput(src,obj,field):
    return [0x59 | (src<<8) | (obj<<12),field]

def _iget_object(dst,obj,field):
    return [0x54 | (dst<<8) | (obj<<12),field]

def _aput(src,arr,idx):
    return [0x4b | (src<<8), arr | (idx<<8)]

def build_probe_units(player_field,field_ids,save_mid):
    f=field_ids
    u=[0x0062,player_field]
    u += _const32(1,SENTINELS['bank']) + _iput(1,0,f['m_bank'])
    u += _const16(1,SENTINELS['lastnegotiations']) + _iput(1,0,f['m_lastnegotiations'])
    u += _const16(3,0)
    u += _iget_object(2,0,f['m_items']) + _const16(4,SENTINELS['items0']) + _aput(4,2,3)
    u += _iget_object(2,0,f['m_sponsors']) + _const16(4,SENTINELS['sponsors0']) + _aput(4,2,3)
    u += _float_const(1,SENTINELS['relationsponsors']) + _iput(1,0,f['m_relationsponsors'])
    u += _float_const(1,SENTINELS['relationboss']) + _iput(1,0,f['m_relationboss'])
    u += _float_const(1,SENTINELS['energy']) + _iput(1,0,f['m_energy'])
    u += _iget_object(2,0,f['m_technique']) + _const16(4,SENTINELS['technique0']) + _aput(4,2,3)
    u += _const16(1,SENTINELS['deplete_technique']) + _iput(1,0,f['m_deplete_technique'])
    u += _const16(1,SENTINELS['iapAgent1']) + _iput(1,0,f['m_iapAgent1'])
    u += [0x106e,save_mid,0x0000,0x000a,0x000e]
    return u

def instruction_hash(d, owner, name):
    methods=[m for m in (d.class_methods(owner) or []) if m[2][1]==name and m[4]]
    if len(methods)!=1: raise ValueError(f'expected one coded method {owner}->{name}, found {len(methods)}')
    code=methods[0][4]
    regs,ins,outs,tries,size,_=d.disasm(code)
    raw=d.b[code+16:code+16+size*2]
    return hashlib.sha256(raw).hexdigest()

def patch_dex(data,dex_name):
    with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f:
        f.write(data); tmp=f.name
    try:
        Dex=_dex_class(); d=Dex(tmp)
        methods=[m for m in (d.class_methods(UTILITY) or []) if m[2][1]==TARGET and m[4]]
        if not methods:return data,False,None
        if len(methods)!=1:raise ValueError(f'expected one {TARGET}, found {len(methods)}')
        _kind,mid,_mt,access,code=methods[0]
        if not (access & 0x8):raise ValueError(f'{TARGET} is not static')
        ret,params,_=proto_signature(d,mid)
        if (ret,params)!=('V',[]):raise ValueError(f'unexpected {TARGET} proto {ret} {params}')
        save_mid=unique_index(d.methods,PLAYER,'p_SaveCareer','method')
        sret,sparams,_=proto_signature(d,save_mid)
        if (sret,sparams)!=('I',[]):raise ValueError(f'unexpected p_SaveCareer proto {sret} {sparams}')
        player_field=unique_index(d.fields,BB,'g_player','field')
        names=('m_bank','m_lastnegotiations','m_items','m_sponsors','m_relationsponsors','m_relationboss','m_energy','m_technique','m_deplete_technique','m_iapAgent1')
        field_ids={n:unique_index(d.fields,PLAYER,n,'field') for n in names}
        save_hash=instruction_hash(d,PLAYER,'p_SaveCareer')
        load_hash=instruction_hash(d,PLAYER,'m_LoadCareer')
        regs,ins,outs,tries,size,_=d.disasm(code)
        if tries:raise ValueError(f'{TARGET} has try handlers')
        if regs<5 or outs<1:raise ValueError(f'{TARGET} lacks registers/outs regs={regs} outs={outs}')
        units=build_probe_units(player_field,field_ids,save_mid)
        if size<len(units):raise ValueError(f'{TARGET} too small {size} < {len(units)}')
        blob=bytearray(data); off=code+16
        struct.pack_into(f'<{size}H',blob,off,*(units+[0]*(size-len(units))))
        blob[12:32]=hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I',blob,8,zlib.adler32(blob[12:]) & 0xffffffff)
        ev={'dex':dex_name,'target':TARGET,'target_method_id':mid,'target_code_off':code,'probe_code_units':len(units),'stock_savecareer_method_id':save_mid,'stock_savecareer_instruction_sha256':save_hash,'stock_loadcareer_instruction_sha256':load_hash,'sentinels':SENTINELS}
        return bytes(blob),True,ev
    finally:
        Path(tmp).unlink(missing_ok=True)

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: patch_stage7_persistence_probe.py INPUT_APK OUTPUT_APK')
    src,dst=map(Path,sys.argv[1:]); entries=[];patched=0;evidence=[]
    with zipfile.ZipFile(src) as zin:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
                data,changed,ev=patch_dex(data,Path(info.filename).name)
                if changed:patched+=1;evidence.append(ev)
            entries.append((info,data))
    if patched!=1:raise SystemExit(f'expected exactly one patched DEX, found {patched}')
    with zipfile.ZipFile(dst,'w') as zout:
        for info,data in entries:
            zi=zipfile.ZipInfo(info.filename,info.date_time); zi.compress_type=info.compress_type;zi.comment=info.comment;zi.extra=info.extra;zi.internal_attr=info.internal_attr;zi.external_attr=info.external_attr;zi.create_system=info.create_system;zi.flag_bits=info.flag_bits
            zout.writestr(zi,data)
    print(json.dumps({'verdict':'STAGE7_TEST_ONLY_PROBE_PATCHED','evidence':evidence},sort_keys=True))
    print(f'Wrote TEST-ONLY Stage7 persistence probe APK: {dst}')

if __name__=='__main__': main()
