#!/usr/bin/env python3
import json, sys, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex

TOKENS=('BadgeStyle1','BadgeStyle2','Badge1Col1','Badge1Col2','Badge2Col1','Badge2Col2','MatchColours')
FIELD_TERMS=('homestyle','kitshirtcol','kitshortscol','badge','shield')
PKG='Lcom/newstargames/newstarsoccer/'


def main():
    if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.json')
    apk,out=Path(sys.argv[1]),Path(sys.argv[2]); report={'string_hits':[],'field_candidates':[],'club_methods':[]}
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for dex_name in sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')):
            p=Path(td)/Path(dex_name).name; p.write_bytes(z.read(dex_name)); d=Dex(p)
            for idx,(cls,fn,ft) in enumerate(d.fields):
                low=fn.lower()
                if cls.startswith(PKG) and any(t in low for t in FIELD_TERMS):
                    report['field_candidates'].append({'dex':dex_name,'field_id':idx,'class':cls,'name':fn,'type':ft})
            for desc in d.types:
                if not desc.startswith(PKG): continue
                methods=d.class_methods(desc)
                for kind,mid,m,acc,code in methods:
                    if not code: continue
                    try: regs,ins,outs,tries,sz,items=d.disasm(code,limit=50000)
                    except Exception: continue
                    hits=[]; field_hits=[]
                    for pos,(off,op,args,raw) in enumerate(items):
                        if op.startswith('const-string') and any(tok in args for tok in TOKENS):
                            hits.append({'offset':off,'op':op,'args':args})
                        if '[field@' in args and any(t in args.lower() for t in FIELD_TERMS):
                            field_hits.append({'offset':off,'op':op,'args':args})
                    if hits:
                        report['string_hits'].append({'dex':dex_name,'class':desc,'method':m[1],'method_id':mid,'hits':hits,'field_hits':field_hits})
                    if desc.endswith('/c_TClub;') and field_hits:
                        report['club_methods'].append({'dex':dex_name,'class':desc,'method':m[1],'method_id':mid,'field_hits':field_hits})
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"BADGE_WRITER_SCAN=PASS string_methods={len(report['string_hits'])} field_candidates={len(report['field_candidates'])} club_methods={len(report['club_methods'])} out={out}")

if __name__=='__main__': main()
