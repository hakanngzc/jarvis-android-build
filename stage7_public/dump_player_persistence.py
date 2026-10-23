#!/usr/bin/env python3
import json, sys, tempfile, zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex

PKG='Lcom/newstargames/newstarsoccer/'
PLAYER_TARGETS={
    'Lcom/newstargames/newstarsoccer/c_TPlayer;',
    'Lcom/newstargames/newstarsoccer/c_TBase_Player;',
}
SAVE_METHOD_TERMS=('playerdata','savecareer','quicksave','loadcareer','completeLoadString'.lower())
SEMANTIC_TERMS=('money','cash','bank','income','spend','wage','salary','contract','sponsor','relationship','relation','boss','team','fan','girl','partner','lifestyle','life','skill','training','train','fitness','pace','power','tech','vision','stamina','confidence','form','energy','boot','agent')
CLASS_TERMS=('Contract','Sponsor','Relation','Lifestyle','Skill','Training','Player')


def semantic_hits(name):
    low=name.lower()
    return sorted({term for term in SEMANTIC_TERMS if term in low})


def main():
    if len(sys.argv)!=3:
        raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT_DIR')
    apk=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
    report={
        'apk':str(apk),
        'player_fields':[],
        'semantic_field_candidates':[],
        'semantic_method_candidates':[],
        'semantic_class_candidates':[],
        'player_methods':[],
        'player_field_accesses':[],
        'save_related_methods':[],
    }
    disasm=[]
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        dex_names=sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex'))
        for dex_name in dex_names:
            p=Path(td)/Path(dex_name).name; p.write_bytes(z.read(dex_name)); d=Dex(p)
            player_field_ids=set()
            for idx,(cls,fn,ft) in enumerate(d.fields):
                if cls in PLAYER_TARGETS:
                    player_field_ids.add(idx)
                    report['player_fields'].append({'dex':dex_name,'field_id':idx,'class':cls,'name':fn,'type':ft,'semantic_hits':semantic_hits(fn)})
                hits=semantic_hits(fn)
                if cls.startswith(PKG) and hits:
                    report['semantic_field_candidates'].append({'dex':dex_name,'field_id':idx,'class':cls,'name':fn,'type':ft,'semantic_hits':hits})
            for desc in d.types:
                if desc.startswith(PKG) and any(t.lower() in desc.lower() for t in CLASS_TERMS):
                    report['semantic_class_candidates'].append({'dex':dex_name,'class':desc})
                if not desc.startswith(PKG):
                    continue
                for kind,mid,m,acc,code in d.class_methods(desc):
                    mh=semantic_hits(m[1])
                    if mh:
                        report['semantic_method_candidates'].append({'dex':dex_name,'class':desc,'method':m[1],'method_id':mid,'semantic_hits':mh})
                    if desc in PLAYER_TARGETS:
                        report['player_methods'].append({'dex':dex_name,'class':desc,'kind':kind,'method':m[1],'method_id':mid,'access':acc,'code_off':code})
                    if not code:
                        continue
                    try: regs,ins,outs,tries,sz,items=d.disasm(code,limit=60000)
                    except Exception: continue
                    accesses=[]
                    for off,op,args,raw in items:
                        if '[field@' not in args:
                            continue
                        for fid in player_field_ids:
                            marker=f'[field@{fid}]'
                            if marker in args:
                                accesses.append({'offset':off,'op':op,'args':args,'write':op.startswith(('iput','sput'))})
                                break
                    if accesses:
                        report['player_field_accesses'].append({'dex':dex_name,'class':desc,'method':m[1],'method_id':mid,'accesses':accesses})
                    lname=m[1].lower()
                    if desc in PLAYER_TARGETS and any(t in lname for t in SAVE_METHOD_TERMS):
                        report['save_related_methods'].append({'dex':dex_name,'class':desc,'method':m[1],'method_id':mid,'code_off':code,'field_accesses':accesses})
                        disasm.append(f'DEX={dex_name}\nCLASS={desc}\nMETHOD={m[1]} id={mid} code={code:#x}\nHEADER regs={regs} ins={ins} outs={outs} tries={tries} units={sz}')
                        for off,op,args,raw in items:
                            disasm.append(f'{off:05x}: {raw:<28} {op:<25} {args}')
                        disasm.append('')
    for key in ('player_fields','semantic_field_candidates','semantic_method_candidates','semantic_class_candidates','player_methods','player_field_accesses','save_related_methods'):
        report[key]=sorted(report[key],key=lambda x:tuple(str(x.get(k,'')) for k in ('dex','class','method','name','field_id','method_id')))
    (out/'stage7-player-persistence-inventory.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    (out/'stage7-player-save-disasm.txt').write_text('\n'.join(disasm)+'\n',encoding='utf-8')
    print('STAGE7_PLAYER_INVENTORY=PASS',
          f"player_fields={len(report['player_fields'])}",
          f"player_methods={len(report['player_methods'])}",
          f"semantic_fields={len(report['semantic_field_candidates'])}",
          f"semantic_methods={len(report['semantic_method_candidates'])}",
          f"save_methods={len(report['save_related_methods'])}")

if __name__=='__main__': main()
