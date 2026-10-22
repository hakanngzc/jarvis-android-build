import struct, json, sys
from pathlib import Path

ACC={0x1:'public',0x2:'private',0x4:'protected',0x8:'static',0x10:'final',0x20:'synchronized',0x40:'volatile/bridge',0x80:'transient/varargs',0x100:'native',0x200:'interface',0x400:'abstract',0x800:'strict',0x1000:'synthetic',0x2000:'annotation',0x4000:'enum',0x10000:'constructor',0x20000:'declared-synchronized'}
def flags(v): return [name for bit,name in ACC.items() if v & bit]
class Dex:
    def __init__(self,path):
        self.path=str(path); self.b=Path(path).read_bytes(); b=self.b
        if not b.startswith(b'dex\n'): raise ValueError(path)
        self.string_n,self.string_off=struct.unpack_from('<II',b,0x38); self.type_n,self.type_off=struct.unpack_from('<II',b,0x40); self.proto_n,self.proto_off=struct.unpack_from('<II',b,0x48); self.field_n,self.field_off=struct.unpack_from('<II',b,0x50); self.method_n,self.method_off=struct.unpack_from('<II',b,0x58); self.class_n,self.class_off=struct.unpack_from('<II',b,0x60)
        self.strings=[self._string(struct.unpack_from('<I',b,self.string_off+4*i)[0]) for i in range(self.string_n)]
        self.types=[self.strings[struct.unpack_from('<I',b,self.type_off+4*i)[0]] for i in range(self.type_n)]
        self.protos=[]
        for i in range(self.proto_n):
            _,ret,params=struct.unpack_from('<III',b,self.proto_off+12*i); ps=[]
            if params:
                n=struct.unpack_from('<I',b,params)[0]; ps=[self.types[struct.unpack_from('<H',b,params+4+2*j)[0]] for j in range(n)]
            self.protos.append((self.types[ret],ps))
        self.fields=[]
        for i in range(self.field_n):
            ci,ti,ni=struct.unpack_from('<HHI',b,self.field_off+8*i); self.fields.append((self.types[ci],self.strings[ni],self.types[ti]))
        self.methods=[]
        for i in range(self.method_n):
            ci,pi,ni=struct.unpack_from('<HHI',b,self.method_off+8*i); self.methods.append((self.types[ci],self.strings[ni],self.protos[pi]))
        self.class_defs=[]
        for i in range(self.class_n):
            ci,access,superi,interfaces,source,ann,data,_=struct.unpack_from('<8I',b,self.class_off+32*i); self.class_defs.append({'descriptor':self.types[ci],'access':access,'super':None if superi==0xffffffff else self.types[superi],'interfaces_off':interfaces,'source':None if source==0xffffffff else self.strings[source],'data_off':data})
    def uleb(self,o):
        r=0;s=0
        while True:
            x=self.b[o];o+=1;r|=(x&0x7f)<<s
            if x<128:return r,o
            s+=7
    def _string(self,o):
        _,o=self.uleb(o); e=self.b.index(0,o); return self.b[o:e].decode('utf-8','replace')
    def class_data(self,cd):
        o=cd['data_off']; out={'static_fields':[],'instance_fields':[],'direct_methods':[],'virtual_methods':[]}
        if not o:return out
        sf,o=self.uleb(o); inf,o=self.uleb(o); dm,o=self.uleb(o); vm,o=self.uleb(o)
        for kind,count in [('static_fields',sf),('instance_fields',inf)]:
            idx=0
            for _ in range(count):
                diff,o=self.uleb(o); idx+=diff; access,o=self.uleb(o); cls,name,typ=self.fields[idx]; out[kind].append({'index':idx,'class':cls,'name':name,'type':typ,'access':access,'flags':flags(access)})
        for kind,count in [('direct_methods',dm),('virtual_methods',vm)]:
            idx=0
            for _ in range(count):
                diff,o=self.uleb(o); idx+=diff; access,o=self.uleb(o); code,o=self.uleb(o); cls,name,proto=self.methods[idx]; out[kind].append({'index':idx,'class':cls,'name':name,'return':proto[0],'params':proto[1],'access':access,'flags':flags(access),'code_off':code})
        return out

def app_classes(dexes):
    rows=[]
    for dn,d in dexes:
        for cd in d.class_defs:
            if not cd['descriptor'].startswith('Lcom/newstargames/newstarsoccer/'): continue
            rows.append({'dex':dn,**cd,**d.class_data(cd)})
    return rows
