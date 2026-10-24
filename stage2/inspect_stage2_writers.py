#!/usr/bin/env python3
import argparse, hashlib, json, re, tempfile, zipfile
from pathlib import Path
from residual_static.nss_residual_static_analysis import Dex

APP='Lcom/newstargames/newstarsoccer/'
TARGETS={
  (APP+'c_TContractOffer;','p_SignContract'):'contract_accept_and_transfer_commit',
  (APP+'c_TScreen_Contract;','m_ButtonReject'):'contract_reject_commit',
  (APP+'c_TScreen_Retirement;','m_ButtonPlay'):'retirement_commit',
}

def code_digest(d, code_off):
    if not code_off: return {'instruction_units':0,'insns_sha256':None}
    size=int.from_bytes(d.b[code_off+12:code_off+16],'little')
    raw=d.b[code_off+16:code_off+16+size*2]
    return {'instruction_units':size,'insns_sha256':hashlib.sha256(raw).hexdigest()}

def inspect(base_apk: Path):
    with tempfile.TemporaryDirectory(prefix='nss-stage2-writers-') as td:
        td=Path(td); dexes=[]
        with zipfile.ZipFile(base_apk) as z:
            for name in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
                p=td/name; p.write_bytes(z.read(name)); dexes.append((name,Dex(p)))
        found={}; callers={key:[] for key in TARGETS}
        for dexname,d in dexes:
            for cd in d.class_defs:
                if not cd['descriptor'].startswith(APP): continue
                data=d.class_data(cd)
                for m in data['methods']:
                    key=(cd['descriptor'],m['name'])
                    if key in TARGETS:
                        found[key]={
                          'purpose':TARGETS[key],'class':cd['descriptor'],'method':m['name'],'dex':dexname,
                          'return':m['return'],'params':m['params'],'access':m.get('access'),
                          **code_digest(d,m['code_off'])
                        }
                    if not m['code_off']: continue
                    _,methodrefs,_=d.method_refs(m['code_off'])
                    for target in TARGETS:
                        if target in methodrefs:
                            callers[target].append({'class':cd['descriptor'],'method':m['name'],'dex':dexname})
        missing=[f'{c}->{m}' for c,m in TARGETS if (c,m) not in found]
        if missing: raise SystemExit('missing target writers: '+', '.join(missing))
        out=[]
        for key,purpose in TARGETS.items():
            row=found[key]; row['callers']=sorted(callers[key],key=lambda x:(x['class'],x['method'],x['dex'])); out.append(row)
        return {'schema':1,'targets':out}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('base_apk',type=Path); ap.add_argument('--out',required=True,type=Path); a=ap.parse_args()
    data=inspect(a.base_apk); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(data,indent=2),encoding='utf-8')
    for t in data['targets']:
        print(t['purpose'],t['class'],t['method'],'params=',t['params'],'ret=',t['return'],'units=',t['instruction_units'],'sha=',t['insns_sha256'],'callers=',len(t['callers']))
        for c in t['callers'][:20]: print('  caller',c['class'],c['method'],c['dex'])
if __name__=='__main__': main()
