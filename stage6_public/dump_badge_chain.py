#!/usr/bin/env python3
import sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex
TARGETS=[
 ('Lcom/newstargames/newstarsoccer/c_TClub;','m_CreateClub'),
 ('Lcom/newstargames/newstarsoccer/c_TScreen_ClubFixtures;','m_SetUpTeamShield'),
 ('Lcom/newstargames/newstarsoccer/c_AScreen_Match;','m_SetUpTeamShield'),
 ('Lcom/newstargames/newstarsoccer/c_AtlasManager;','m_GetAtlasedImage'),
 ('Lcom/newstargames/newstarsoccer/c_ImageAsset;',''),
]
def main():
 if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.txt')
 apk,out=Path(sys.argv[1]),Path(sys.argv[2]);lines=[];hits=0
 with zipfile.ZipFile(apk) as z,tempfile.TemporaryDirectory() as td:
  dexes=[]
  for dn in sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')):
   p=Path(td)/Path(dn).name;p.write_bytes(z.read(dn));dexes.append((dn,Dex(p)))
  for cls,needle in TARGETS:
   for dn,d in dexes:
    methods=d.class_methods(cls)
    if not methods: continue
    for kind,mid,m,acc,code in methods:
     if needle and needle.lower() not in m[1].lower(): continue
     hits+=1;lines+=['',f'DEX={dn}',f'CLASS={cls}',f'METHOD kind={kind} id={mid} name={m[1]} access={acc:#x} code={code:#x}']
     if code:
      regs,ins,outs,tries,sz,items=d.disasm(code,limit=30000);lines.append(f'HEADER regs={regs} ins={ins} outs={outs} tries={tries} units={sz}')
      for off,op,args,raw in items: lines.append(f'{off:05x}: {raw:<28} {op:<25} {args}')
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(f'BADGE_CHAIN_DISASM=PASS methods={hits} out={out}')
if __name__=='__main__':main()
