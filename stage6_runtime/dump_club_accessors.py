#!/usr/bin/env python3
import struct,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex

TARGET_NAMES={'m_LoadClub','m_GetListByNationId','p_GetClubData','m_SetUpTeamShield'}


def proto_sig(d,pi):
    off=d.proto_off+12*pi
    _,ret,params=struct.unpack_from('<III',d.b,off)
    ps=[]
    if params:
        n=struct.unpack_from('<I',d.b,params)[0]
        for i in range(n):
            ti=struct.unpack_from('<H',d.b,params+4+2*i)[0]
            ps.append(d.types[ti])
    return '('+''.join(ps)+')'+d.types[ret]


def iter_methods(d):
    b=d.b
    for j in range(d.class_n):
        vals=struct.unpack_from('<8I',b,d.class_off+32*j); ci,data_off=vals[0],vals[6]
        if not data_off: continue
        desc=d.types[ci]; o=data_off
        sf,o=d.uleb(o); inf,o=d.uleb(o); dm,o=d.uleb(o); vm,o=d.uleb(o)
        for _ in range(sf+inf): _,o=d.uleb(o); _,o=d.uleb(o)
        for kind,count in [('direct',dm),('virtual',vm)]:
            mid=0
            for _ in range(count):
                diff,o=d.uleb(o); mid+=diff; access,o=d.uleb(o); code,o=d.uleb(o)
                yield desc,kind,mid,access,code


def main():
    if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.txt')
    apk,out=Path(sys.argv[1]),Path(sys.argv[2]); lines=[]
    with zipfile.ZipFile(apk) as z,tempfile.TemporaryDirectory() as td:
        for dn in sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')):
            dp=Path(td)/Path(dn).name; dp.write_bytes(z.read(dn)); d=Dex(dp)
            target_ids={i for i,(cls,name,pi) in enumerate(d.methods) if name in TARGET_NAMES or ('Club' in name and ('Get' in name or 'Load' in name))}
            if not target_ids: continue
            lines.append('===== '+dn+' =====')
            for i in sorted(target_ids):
                cls,name,pi=d.methods[i]
                lines.append(f'DEF method@{i} {cls}->{name}{proto_sig(d,pi)}')
            for desc,kind,mid,access,code in iter_methods(d):
                if not code: continue
                try: items=d.disasm(code,limit=30000)[-1]
                except Exception: continue
                hits=[]
                for off,op,args,raw in items:
                    if '[method@' not in args: continue
                    for tid in target_ids:
                        if f'[method@{tid}]' in args: hits.append((off,op,args,raw)); break
                if hits:
                    _,mn,pi=d.methods[mid]
                    lines.append(f'CALLER {desc}->{mn}{proto_sig(d,pi)} access={access:#x}')
                    for off,op,args,raw in hits: lines.append(f'  {off:05x}: {raw:<28} {op:<20} {args}')
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('STAGE6_CLUB_ACCESSORS_DUMP=PASS out='+str(out))

if __name__=='__main__': main()
