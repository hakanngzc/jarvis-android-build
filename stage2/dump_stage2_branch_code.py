#!/usr/bin/env python3
import argparse, json, re, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dex_inspect import Dex

APP='Lcom/newstargames/newstarsoccer/'
CLASSES={
  APP+'c_TContractOffer;': ['p_SignContract','p_DoNegotiation','p_IncreaseOffer'],
  APP+'c_TScreen_Contract;': ['m_SetUpScreen','m_ButtonAccept','m_ButtonReject','m_ButtonNegotiate'],
  APP+'c_TScreen_Retirement;': ['m_SetUpScreen','m_ButtonPlay'],
  APP+'c_TPlayer;': ['p_Retire','p_QuickSave'],
  APP+'c_TScreen_Message;': ['m_DoCallFunction'],
}

def dump(apk: Path):
    result={'schema':1,'classes':{}}
    with tempfile.TemporaryDirectory(prefix='nss-stage2-dump-') as td:
        td=Path(td)
        dexes=[]
        with zipfile.ZipFile(apk) as z:
            for name in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
                p=td/name; p.write_bytes(z.read(name)); dexes.append((name,Dex(p)))
        for desc,wanted in CLASSES.items():
            hit=None
            for dn,d in dexes:
                methods=d.class_methods(desc)
                if methods:
                    hit=(dn,d,methods); break
            if not hit:
                result['classes'][desc]={'missing':True}; continue
            dn,d,methods=hit
            row={'dex':dn,'declared_fields':[{'name':n,'type':t} for c,n,t in d.fields if c==desc],'methods':{}}
            for kind,mid,m,acc,code in methods:
                name=m[1]
                if name not in wanted: continue
                mr={'kind':kind,'method_index':mid,'access':acc,'code_off':code}
                if code:
                    regs,ins,outs,tries,units,items=d.disasm(code)
                    mr.update({'registers':regs,'ins':ins,'outs':outs,'tries':tries,'instruction_units':units,
                      'instructions':[{'off':off,'op':op,'args':args,'raw':raw} for off,op,args,raw in items]})
                row['methods'][name]=mr
            result['classes'][desc]=row
    return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('base_apk',type=Path); ap.add_argument('--out',required=True,type=Path); a=ap.parse_args()
    data=dump(a.base_apk); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(data,indent=2),encoding='utf-8')
    for cls,row in data['classes'].items():
        print('\nCLASS',cls,'DEX',row.get('dex'))
        print('FIELDS',[(x['name'],x['type']) for x in row.get('declared_fields',[])])
        for name,m in row.get('methods',{}).items():
            print('METHOD',name,'regs',m.get('registers'),'ins',m.get('ins'),'units',m.get('instruction_units'))
            for i in m.get('instructions',[]):
                if i['op'].startswith(('invoke','iget','iput','sget','sput','new-instance','const-string')):
                    print(f"  {i['off']:04x} {i['op']} {i['args']}")
if __name__=='__main__': main()
