#!/usr/bin/env python3
from __future__ import annotations
import hashlib, re, struct, sys, tempfile, zlib, zipfile
from pathlib import Path

BB='Lcom/newstargames/newstarsoccer/bb_;'
UTILITY='Lcom/newstargames/newstarsoccer/bb_GSPlayerUtility;'
PLAYER='Lcom/newstargames/newstarsoccer/c_TPlayer;'
TARGET='g_GSPlayerPlayMatches'
SENTINELS={
    'm_bank':24680,
    'm_items[0]':23117,
    'm_sponsors[0]':31415,
    'm_spenttime':27182,
    'm_technique[0]':22361,
    'm_iapAgent1':19873,
}

class Dex:
    def __init__(self,path: str|Path):
        self.b=Path(path).read_bytes(); b=self.b
        if not b.startswith(b'dex\n'): raise ValueError('not dex')
        vals=struct.unpack_from('<20I',b,0x38)
        (self.string_n,self.string_off,self.type_n,self.type_off,self.proto_n,self.proto_off,
         self.field_n,self.field_off,self.method_n,self.method_off,self.class_n,self.class_off,*_)=vals
        self.strings=[self._string(struct.unpack_from('<I',b,self.string_off+4*i)[0]) for i in range(self.string_n)]
        self.types=[self.strings[struct.unpack_from('<I',b,self.type_off+4*i)[0]] for i in range(self.type_n)]
        self.methods=[]
        for i in range(self.method_n):
            ci,pi,ni=struct.unpack_from('<HHI',b,self.method_off+8*i); self.methods.append((self.types[ci],self.strings[ni],pi))
        self.fields=[]
        for i in range(self.field_n):
            ci,ti,ni=struct.unpack_from('<HHI',b,self.field_off+8*i); self.fields.append((self.types[ci],self.strings[ni],self.types[ti]))
    def uleb(self,o):
        r=s=0
        while True:
            x=self.b[o];o+=1;r|=(x&0x7f)<<s
            if x<128:return r,o
            s+=7
    def _string(self,o):
        _,o=self.uleb(o); e=self.b.index(0,o); return self.b[o:e].decode('utf-8','replace')
    def class_methods(self,desc):
        b=self.b
        for j in range(self.class_n):
            vals=struct.unpack_from('<8I',b,self.class_off+32*j); class_idx=vals[0]; data_off=vals[6]
            if self.types[class_idx]!=desc or not data_off: continue
            o=data_off; sf,o=self.uleb(o); inf,o=self.uleb(o); dm,o=self.uleb(o); vm,o=self.uleb(o)
            for _ in range(sf+inf): _,o=self.uleb(o);_,o=self.uleb(o)
            out=[]
            for kind,count in [('direct',dm),('virtual',vm)]:
                mid=0
                for _ in range(count):
                    diff,o=self.uleb(o); mid+=diff; access,o=self.uleb(o); code,o=self.uleb(o)
                    out.append((kind,mid,self.methods[mid],access,code))
            return out
        return []
    def code_header(self,code):
        regs,ins,outs,tries=struct.unpack_from('<4H',self.b,code); _debug,sz=struct.unpack_from('<2I',self.b,code+8)
        return regs,ins,outs,tries,sz

def unique_index(items,owner,name,kind):
    hits=[i for i,item in enumerate(items) if item[0]==owner and item[1]==name]
    if len(hits)!=1: raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]

def proto_signature(d:Dex,mid:int):
    _owner,_name,proto_id=d.methods[mid]
    shorty_idx,ret_idx,params_off=struct.unpack_from('<III',d.b,d.proto_off+12*proto_id)
    params=[]
    if params_off:
        count=struct.unpack_from('<I',d.b,params_off)[0]
        params=[d.types[struct.unpack_from('<H',d.b,params_off+4+2*i)[0]] for i in range(count)]
    return d.types[ret_idx],params,d.strings[shorty_idx]

def _const16(reg:int,value:int):
    if not -32768 <= value <= 32767: raise ValueError(f'const/16 out of range: {value}')
    return [0x13 | (reg<<8), value & 0xffff]
def _sget_object(reg:int,field:int): return [0x62 | (reg<<8),field]
def _iget_object(dst:int,obj:int,field:int): return [0x54 | (dst<<8) | (obj<<12),field]
def _iput(src:int,obj:int,field:int): return [0x59 | (src<<8) | (obj<<12),field]
def _aput(src:int,array:int,index:int): return [0x4b | (src<<8), array | (index<<8)]
def _invoke_virtual_one(reg:int,method:int): return [0x106e,method,reg & 0xf]

def build_probe_units(mode:str, fields:dict[str,int], save_mid:int):
    if mode not in ('mutate','save-only'): raise ValueError(f'unsupported mode {mode}')
    u=[]
    u += _sget_object(0,fields['g_player'])
    if mode=='mutate':
        u += _const16(1,SENTINELS['m_bank']); u += _iput(1,0,fields['m_bank'])
        u += _iget_object(2,0,fields['m_items']); u += [0x0312]; u += _const16(4,SENTINELS['m_items[0]']); u += _aput(4,2,3)
        u += _iget_object(2,0,fields['m_sponsors']); u += [0x0312]; u += _const16(4,SENTINELS['m_sponsors[0]']); u += _aput(4,2,3)
        u += _const16(1,SENTINELS['m_spenttime']); u += _iput(1,0,fields['m_spenttime'])
        u += _iget_object(2,0,fields['m_technique']); u += [0x0312]; u += _const16(4,SENTINELS['m_technique[0]']); u += _aput(4,2,3)
        u += _const16(1,SENTINELS['m_iapAgent1']); u += _iput(1,0,fields['m_iapAgent1'])
    u += _invoke_virtual_one(0,save_mid)
    u += [0x010a,0x000e]
    return u

def patch_dex(data:bytes,dex_name:str,mode:str):
    with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f: f.write(data); tmp=Path(f.name)
    try:
        d=Dex(tmp)
        methods=[m for m in d.class_methods(UTILITY) if m[2][1]==TARGET and m[4]]
        if not methods:return data,False,None
        if len(methods)!=1:raise ValueError(f'expected one {TARGET}, found {len(methods)}')
        _kind,mid,_m,access,code=methods[0]
        if not (access & 0x8):raise ValueError(f'{TARGET} is not static')
        ret,params,shorty=proto_signature(d,mid)
        if (ret,params)!=('V',[]):raise ValueError(f'unexpected {TARGET} proto: {shorty} {ret} {params}')
        save_mid=unique_index(d.methods,PLAYER,'p_SaveCareer','method')
        sret,sparams,sshorty=proto_signature(d,save_mid)
        if (sret,sparams)!=('I',[]):raise ValueError(f'unexpected p_SaveCareer proto: {sshorty} {sret} {sparams}')
        fields={'g_player':unique_index(d.fields,BB,'g_player','field')}
        for name in ('m_bank','m_items','m_sponsors','m_spenttime','m_technique','m_iapAgent1'):
            fields[name]=unique_index(d.fields,PLAYER,name,'field')
        regs,ins,outs,tries,size=d.code_header(code)
        if tries:raise ValueError(f'{TARGET} has try handlers')
        if regs<5 or outs<1:raise ValueError(f'{TARGET} lacks registers/outs: regs={regs} outs={outs}')
        units=build_probe_units(mode,fields,save_mid)
        if size<len(units):raise ValueError(f'{TARGET} too small: {size} < {len(units)}')
        blob=bytearray(data); off=code+16
        struct.pack_into(f'<{size}H',blob,off,*(units+[0]*(size-len(units))))
        blob[12:32]=hashlib.sha1(blob[32:]).digest(); struct.pack_into('<I',blob,8,zlib.adler32(blob[12:]) & 0xffffffff)
        ev={
            'dex':dex_name,'mode':mode,'target':TARGET,'target_method_index':mid,'code_off':code,
            'stock_save_method':'c_TPlayer.p_SaveCareer()I','stock_save_method_index':save_mid,
            'sentinels':SENTINELS if mode=='mutate' else {},'field_indexes':fields,
            'original_code_units':size,'probe_code_units':len(units),
        }
        return bytes(blob),True,ev
    finally: tmp.unlink(missing_ok=True)

def patch_apk(src:Path,dst:Path,mode:str):
    entries=[];patched=0;evidence=[]
    with zipfile.ZipFile(src) as zin:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
                data,changed,ev=patch_dex(data,Path(info.filename).name,mode)
                if changed:patched+=1;evidence.append(ev)
            entries.append((info,data))
    if patched!=1:raise ValueError(f'expected exactly one patched DEX, found {patched}')
    with zipfile.ZipFile(dst,'w') as zout:
        for info,data in entries:
            zi=zipfile.ZipInfo(info.filename,info.date_time);zi.compress_type=info.compress_type;zi.comment=info.comment;zi.extra=info.extra;zi.internal_attr=info.internal_attr;zi.external_attr=info.external_attr;zi.create_system=info.create_system;zi.flag_bits=info.flag_bits;zout.writestr(zi,data)
    return evidence[0]

def main():
    if len(sys.argv)!=4:raise SystemExit('usage: patch_stage7_persistence_probe.py INPUT_APK OUTPUT_APK mutate|save-only')
    src,dst=map(Path,sys.argv[1:3]);mode=sys.argv[3]
    ev=patch_apk(src,dst,mode)
    print('STAGE7_TEST_ONLY_PROBE '+repr(ev))
    print(f'Wrote TEST-ONLY Stage7 {mode} probe APK: {dst}')
if __name__=='__main__':main()
