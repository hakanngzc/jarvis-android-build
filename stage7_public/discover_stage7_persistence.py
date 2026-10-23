#!/usr/bin/env python3
import json,re,sys,tempfile,zipfile
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex

PKG='Lcom/newstargames/newstarsoccer/'
PLAYER=PKG+'c_TPlayer;'
FOCUS_CLASSES=(
    'c_TPlayer','c_TContractOffer','c_TScreen_Contract','c_TScreen_Relationships',
    'c_TScreen_Skills','c_TScreen_SkillChoice','c_TScreen_BootShop','c_TScreen_Casino',
    'c_TScreen_GameMenu','c_TScreen_DesiredTransfer','c_TScreen_Message',
)
TERMS=(
    'bank','money','cash','wage','salary','income','spend','cost','price','bonus','fee','sponsor',
    'contract','transfer','negotiat','agent','boot','item','owned','purchase',
    'relationship','relation','boss','team','fan','girlfriend','partner','lifestyle','casino',
    'skill','pace','power','technique','vision','setpiece','set_piece','defence','defense',
    'training','practice','energy','nrg','fitness','trainer','coach','progress','rating',
)
SAVE_TERMS=('save','load','serial','data','career','quick')


def interesting(name):
    low=name.lower()
    return any(t in low for t in TERMS)


def focus_class(desc):
    return any(desc.endswith('/'+n+';') for n in FOCUS_CLASSES)


def main():
    if len(sys.argv)!=3:
        raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.json')
    apk=Path(sys.argv[1]); out=Path(sys.argv[2])
    report={
        'apk':str(apk),'player_fields':[],'candidate_fields':[],
        'field_access_methods':[],'focus_methods':[],'player_save_load_methods':[],
    }
    candidate_ids_by_dex={}
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for dex_name in sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')):
            p=Path(td)/Path(dex_name).name; p.write_bytes(z.read(dex_name)); d=Dex(p)
            ids=set()
            for fid,(cls,fn,ft) in enumerate(d.fields):
                if cls==PLAYER:
                    row={'dex':dex_name,'field_id':fid,'class':cls,'name':fn,'type':ft}
                    report['player_fields'].append(row)
                    if interesting(fn):
                        report['candidate_fields'].append(row); ids.add(fid)
                elif cls.startswith(PKG) and interesting(fn):
                    row={'dex':dex_name,'field_id':fid,'class':cls,'name':fn,'type':ft}
                    report['candidate_fields'].append(row); ids.add(fid)
            candidate_ids_by_dex[dex_name]=ids

            for desc in d.types:
                if not desc.startswith(PKG): continue
                methods=d.class_methods(desc)
                if not methods: continue
                for kind,mid,m,acc,code in methods:
                    mn=m[1]
                    if not code: continue
                    needs_scan=focus_class(desc) or any(t in mn.lower() for t in SAVE_TERMS)
                    # We must still scan other methods for writes/reads to the candidate fields.
                    try: regs,ins,outs,tries,sz,items=d.disasm(code,limit=60000)
                    except Exception: continue
                    hits=[]
                    for off,op,args,raw in items:
                        mm=re.search(r'\[field@(\d+)\]',args)
                        if not mm: continue
                        fid=int(mm.group(1))
                        if fid in ids:
                            cls,fn,ft=d.fields[fid]
                            hits.append({'offset':off,'op':op,'field_id':fid,'class':cls,'name':fn,'type':ft})
                    if hits:
                        report['field_access_methods'].append({
                            'dex':dex_name,'class':desc,'method':mn,'method_id':mid,'hits':hits,
                        })
                    if needs_scan:
                        player_hits=[h for h in hits if h['class']==PLAYER]
                        if player_hits or focus_class(desc):
                            report['focus_methods'].append({
                                'dex':dex_name,'class':desc,'method':mn,'method_id':mid,'player_hits':player_hits,
                            })
                        if desc==PLAYER and any(t in mn.lower() for t in SAVE_TERMS):
                            report['player_save_load_methods'].append({
                                'dex':dex_name,'class':desc,'method':mn,'method_id':mid,'player_hits':player_hits,
                            })

    # Normalize and add field-centric reader/writer summaries.
    access=defaultdict(lambda:{'reads':[],'writes':[],'other':[]})
    for m in report['field_access_methods']:
        for h in m['hits']:
            key=f"{h['class']}->{h['name']}:{h['type']}"
            dst={'dex':m['dex'],'class':m['class'],'method':m['method'],'offset':h['offset'],'op':h['op']}
            if h['op'].startswith(('iget','sget')): access[key]['reads'].append(dst)
            elif h['op'].startswith(('iput','sput')): access[key]['writes'].append(dst)
            else: access[key]['other'].append(dst)
    report['field_access_summary']=dict(sorted(access.items()))
    report['player_fields']=sorted(report['player_fields'],key=lambda x:x['name'])
    report['candidate_fields']=sorted(report['candidate_fields'],key=lambda x:(x['class'],x['name']))
    report['field_access_methods']=sorted(report['field_access_methods'],key=lambda x:(x['class'],x['method'],x['method_id']))
    report['focus_methods']=sorted(report['focus_methods'],key=lambda x:(x['class'],x['method'],x['method_id']))
    report['player_save_load_methods']=sorted(report['player_save_load_methods'],key=lambda x:x['method'])
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('STAGE7_DISCOVERY=PASS '+
          f"player_fields={len(report['player_fields'])} candidates={len(report['candidate_fields'])} "+
          f"access_methods={len(report['field_access_methods'])} save_load_methods={len(report['player_save_load_methods'])} out={out}")

if __name__=='__main__': main()
