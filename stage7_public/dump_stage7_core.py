#!/usr/bin/env python3
import sys,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'stage1_public'))
from dex_inspect import Dex

TARGETS={
'Lcom/newstargames/newstarsoccer/c_TPlayer;':{
'p_AwardStarbux','p_SpendStarbux','p_UpdateBank','p_GetBankBalance','p_GetPlayerData','m_LoadCareer',
'p_UpdateRelationship','p_GetRelationship','p_GetLifestyle','p_SetPace','p_SetPower','p_SetTechnique','p_SetVision','p_SetSetPieces',
'p_OfferSponsorship','p_GetSponsorAmount','m_DepleteContracts','p_HireTrainer1'
},
'Lcom/newstargames/newstarsoccer/c_TContractOffer;':{'p_SignContract','m_GetOffer'},
'Lcom/newstargames/newstarsoccer/bb_GSPlayerUtility;':{
'g_GSPlayerAwardWages','g_GSUpdateRelationship','g_GSUpdatePlayerRelationships','g_GSUpdateLifestyleItems','g_GSCheckSponsorship','g_GSSetStartSkills','g_GSMatchRecovery'
},
'Lcom/newstargames/newstarsoccer/c_TMatch;':{'m_TrainingSuccess','m_TrainingFailure'},
'Lcom/newstargames/newstarsoccer/c_Product_Item;':{'p_Buy','p_TryBuy'},
'Lcom/newstargames/newstarsoccer/c_Product_Vehicle;':{'p_Buy','p_TryBuy'},
'Lcom/newstargames/newstarsoccer/c_Product_Property;':{'p_Buy','p_TryBuy'},
'Lcom/newstargames/newstarsoccer/c_TScreen_Relationships;':{'m_ButtonBoss','m_ButtonTeam','m_ButtonFans','m_ButtonGirlfriend','m_ButtonSponsors'},
}

def main():
    if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.txt')
    apk=Path(sys.argv[1]); out=Path(sys.argv[2]); lines=[]; found=[]
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for dn in sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')):
            p=Path(td)/Path(dn).name; p.write_bytes(z.read(dn)); d=Dex(p)
            for cls,names in TARGETS.items():
                for kind,mid,m,acc,code in d.class_methods(cls) or []:
                    if m[1] not in names: continue
                    found.append((cls,m[1])); lines += [f'DEX={dn}',f'CLASS={cls}',f'METHOD={m[1]} id={mid} access={acc:#x} code={code:#x}']
                    if code:
                        regs,ins,outs,tries,sz,items=d.disasm(code,limit=60000)
                        lines.append(f'HEADER regs={regs} ins={ins} outs={outs} tries={tries} units={sz}')
                        for off,op,args,raw in items: lines.append(f'{off:05x}: {raw:<28} {op:<25} {args}')
                    lines.append('')
    missing=sorted((c,m) for c,ms in TARGETS.items() for m in ms if (c,m) not in found)
    lines.insert(0,'MISSING='+';'.join(f'{c}->{m}' for c,m in missing))
    lines.insert(0,f'FOUND={len(found)} EXPECTED={sum(map(len,TARGETS.values()))}')
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'STAGE7_CORE_DUMP=PASS found={len(found)} missing={len(missing)} out={out}')
    if missing: print('MISSING_TARGETS='+';'.join(f'{c}->{m}' for c,m in missing))

if __name__=='__main__': main()
