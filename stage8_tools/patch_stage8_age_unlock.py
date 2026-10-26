#!/usr/bin/env python3
from __future__ import annotations
import hashlib,re,struct,sys,tempfile,zlib,zipfile
from pathlib import Path

PLAYER='Lcom/newstargames/newstarsoccer/c_TPlayer;'
TARGET_METHOD='p_GetAge'
TARGET_AGE=18

class Dex:
    def __init__(self,path):
        self.b=Path(path).read_bytes(); b=self.b
        if not b.startswith(b'dex\n'): raise ValueError('not dex')
        vals=struct.unpack_from('<20I',b,0x38)
        (self.string_n,self.string_off,self.type_n,self.type_off,self.proto_n,self.proto_off,
         self.field_n,self.field_off,self.method_n,self.method_off,self.class_n,self.class_off,*_)=vals
        self.strings=[self._string(struct.unpack_from('<I',b,self.string_off+4*i)[0]) for i in range(self.string_n)]
        self.types=[self.strings[struct.unpack_from('<I',b,self.type_off+4*i)[0]] for i in range(self.type_n)]
        self.methods=[]
        for i in range(self.method_n):
            ci,pi,ni=struct.unpack_from('<HHI',b,self.method_off+8*i)
            self.methods.append((self.types[ci],self.strings[ni],pi))
    def uleb(self,o):
        r=s=0
        while True:
            x=self.b[o];o+=1;r|=(x&0x7f)<<s
            if x<128:return r,o
            s+=7
    def _string(self,o):
        _,o=self.uleb(o);e=self.b.index(0,o);return self.b[o:e].decode('utf-8','replace')
    def class_methods(self,desc):
        b=self.b
        for j in range(self.class_n):
            vals=struct.unpack_from('<8I',b,self.class_off+32*j);class_idx=vals[0];data_off=vals[6]
            if self.types[class_idx]!=desc or not data_off:continue
            o=data_off;sf,o=self.uleb(o);inf,o=self.uleb(o);dm,o=self.uleb(o);vm,o=self.uleb(o)
            for _ in range(sf+inf):_,o=self.uleb(o);_,o=self.uleb(o)
            out=[]
            for kind,count in [('direct',dm),('virtual',vm)]:
                mid=0
                for _ in range(count):
                    diff,o=self.uleb(o);mid+=diff;access,o=self.uleb(o);code,o=self.uleb(o)
                    out.append((kind,mid,self.methods[mid],access,code))
            return out
        return []

def proto_signature(d:Dex,mid:int):
    _owner,_name,proto_id=d.methods[mid]
    shorty_idx,ret_idx,params_off=struct.unpack_from('<III',d.b,d.proto_off+12*proto_id)
    params=[]
    if params_off:
        count=struct.unpack_from('<I',d.b,params_off)[0]
        params=[d.types[struct.unpack_from('<H',d.b,params_off+4+2*i)[0]] for i in range(count)]
    return d.types[ret_idx],params,d.strings[shorty_idx]

def build_age_units(age:int=TARGET_AGE):
    if not -32768 <= age <= 32767: raise ValueError('age literal out of const/16 range')
    return [0x0013,age & 0xffff,0x000f]  # const/16 v0, age; return v0

def patch_dex(data:bytes,dex_name:str):
    with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f:f.write(data);tmp=Path(f.name)
    try:
        d=Dex(tmp)
        matches=[m for m in d.class_methods(PLAYER) if m[2][1]==TARGET_METHOD and m[4]]
        if not matches:return data,False,None
        if len(matches)!=1:raise ValueError(f'expected one {TARGET_METHOD}, found {len(matches)}')
        _kind,mid,_m,access,code=matches[0]
        if access & 0x8:raise ValueError('p_GetAge unexpectedly static')
        ret,params,shorty=proto_signature(d,mid)
        if (ret,params)!=('I',[]):raise ValueError(f'unexpected p_GetAge proto: {shorty} {ret} {params}')
        regs,ins,outs,tries=struct.unpack_from('<4H',d.b,code);size=struct.unpack_from('<I',d.b,code+12)[0]
        if tries:raise ValueError('p_GetAge has try handlers')
        if regs<1 or ins<1:raise ValueError(f'unexpected p_GetAge registers: regs={regs} ins={ins}')
        units=build_age_units()
        if size<len(units):raise ValueError(f'p_GetAge too small: {size}')
        blob=bytearray(data);off=code+16
        struct.pack_into(f'<{size}H',blob,off,*(units+[0]*(size-len(units))))
        blob[12:32]=hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I',blob,8,zlib.adler32(blob[12:]) & 0xffffffff)
        ev=f'STAGE8 age unlock: {dex_name} c_TPlayer.p_GetAge()I method@{mid} code=0x{code:x} -> constant {TARGET_AGE}; navigation-only test probe'
        return bytes(blob),True,ev
    finally:tmp.unlink(missing_ok=True)

def patch_apk(src:Path,dst:Path):
    entries=[];patched=0;evidence=[]
    with zipfile.ZipFile(src) as zin:
        for info in zin.infolist():
            data=zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
                data,changed,ev=patch_dex(data,Path(info.filename).name)
                if changed:patched+=1;evidence.append(ev)
            entries.append((info,data))
    if patched!=1:raise ValueError(f'expected exactly one patched DEX, found {patched}')
    with zipfile.ZipFile(dst,'w') as zout:
        for info,data in entries:
            zi=zipfile.ZipInfo(info.filename,info.date_time);zi.compress_type=info.compress_type;zi.comment=info.comment;zi.extra=info.extra;zi.internal_attr=info.internal_attr;zi.external_attr=info.external_attr;zi.create_system=info.create_system;zi.flag_bits=info.flag_bits
            zout.writestr(zi,data)
    return evidence[0]

def main():
    if len(sys.argv)!=3:raise SystemExit('usage: patch_stage8_age_unlock.py INPUT_APK OUTPUT_APK')
    src,dst=map(Path,sys.argv[1:]);ev=patch_apk(src,dst)
    print(ev);print(f'Wrote TEST-ONLY Stage8 later-career age probe APK: {dst}')
if __name__=='__main__':main()
