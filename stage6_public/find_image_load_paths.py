#!/usr/bin/env python3
import json,struct,sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex
NEEDLES=('c_AtlasManager;->m_GetAtlasedImage','c_AtlasManager;->m_TryGetAtlasedImage','c_ResourcesUtils;->m_LoadMyImage','bb_graphics;->g_LoadImage')

def iter_methods(d):
 b=d.b
 for j in range(d.class_n):
  vals=struct.unpack_from('<8I',b,d.class_off+32*j);ci,doff=vals[0],vals[6]
  if not doff: continue
  desc=d.types[ci];o=doff;sf,o=d.uleb(o);inf,o=d.uleb(o);dm,o=d.uleb(o);vm,o=d.uleb(o)
  for _ in range(sf+inf):_,o=d.uleb(o);_,o=d.uleb(o)
  for kind,count in [('direct',dm),('virtual',vm)]:
   mid=0
   for _ in range(count):
    diff,o=d.uleb(o);mid+=diff;acc,o=d.uleb(o);code,o=d.uleb(o)
    yield desc,kind,mid,d.methods[mid],acc,code

def main():
 if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.json')
 apk,out=Path(sys.argv[1]),Path(sys.argv[2]);hits=[]
 with zipfile.ZipFile(apk) as z,tempfile.TemporaryDirectory() as td:
  for dn in sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')):
   p=Path(td)/Path(dn).name;p.write_bytes(z.read(dn));d=Dex(p)
   for desc,kind,mid,m,acc,code in iter_methods(d):
    if not code or not desc.startswith('Lcom/newstargames/newstarsoccer/'): continue
    try:*_,items=d.disasm(code,limit=50000)
    except Exception: continue
    idxs=[];matched=set()
    for i,(_,op,args,_) in enumerate(items):
     for n in NEEDLES:
      if n in args: idxs.append(i);matched.add(n)
    if not idxs: continue
    keep=set()
    for i in idxs: keep.update(range(max(0,i-10),min(len(items),i+11)))
    lines=[]
    for i in sorted(keep):
     off,op,args,raw=items[i];lines.append(f'{i:05d} {off:05x}: {raw:<28} {op:<25} {args}')
    hits.append({'dex':dn,'class':desc,'method':m[1],'method_id':mid,'matched':sorted(matched),'window':lines})
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps({'hits':hits},indent=2)+'\n')
 print(f'IMAGE_LOAD_PATH_SCAN=PASS methods={len(hits)} out={out}')
if __name__=='__main__':main()
