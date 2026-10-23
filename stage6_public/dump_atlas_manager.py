#!/usr/bin/env python3
import io
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex

TARGET='Lcom/newstargames/newstarsoccer/c_AtlasManager;'


def main():
    if len(sys.argv)!=3:
        raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.txt')
    apk=Path(sys.argv[1]); out=Path(sys.argv[2]); lines=[]; found=0
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        dex_names=sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex'))
        for dex_name in dex_names:
            path=Path(td)/Path(dex_name).name
            path.write_bytes(z.read(dex_name))
            d=Dex(path)
            methods=d.class_methods(TARGET)
            if not methods:
                continue
            found+=1
            lines.append(f'DEX={dex_name}')
            lines.append(f'CLASS={TARGET}')
            atlas_types=sorted(t for t in d.types if 'Atlas' in t or 'Atlased' in t)
            lines.append('ATLAS_TYPES='+';'.join(atlas_types))
            for kind,mid,m,acc,code in methods:
                lines.append('')
                lines.append(f'METHOD kind={kind} id={mid} name={m[1]} access={acc:#x} code={code:#x}')
                if not code:
                    continue
                regs,ins,outs,tries,sz,items=d.disasm(code,limit=20000)
                lines.append(f'HEADER regs={regs} ins={ins} outs={outs} tries={tries} units={sz}')
                for off,name,args,raw in items:
                    lines.append(f'{off:05x}: {raw:<28} {name:<25} {args}')
    if found!=1:
        raise SystemExit(f'expected AtlasManager in exactly one dex, found {found}')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'ATLAS_MANAGER_DISASM=PASS methods_dumped={sum(1 for x in lines if x.startswith("METHOD "))} out={out}')

if __name__=='__main__': main()
