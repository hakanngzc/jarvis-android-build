#!/usr/bin/env python3
from __future__ import annotations
import hashlib, re, sys, xml.etree.ElementTree as ET
from pathlib import Path

from stage7_tools.patch_stage7_persistence_probe import SENTINELS

SENTINEL_TEXT={k:str(v) for k,v in SENTINELS.items()}
LABELS={
 'bank':'post contains economy bank sentinel',
 'lastnegotiations':'post contains contract timing sentinel',
 'items0':'post contains ownership item sentinel',
 'sponsors0':'post contains sponsor sentinel',
 'relationsponsors':'post contains sponsor-relation sentinel',
 'relationboss':'post contains relationship sentinel',
 'energy':'post contains energy sentinel',
 'technique0':'post contains skill-array sentinel',
 'deplete_technique':'post contains skill-depletion sentinel',
 'iapAgent1':'post contains staff-contract sentinel',
}

def state_xml(path):
    root=ET.fromstring(Path(path).read_text(encoding='utf-8'))
    vals={n.attrib.get('name'):(n.text or '') for n in root.findall('string')}
    state=vals.get('.monkeystate') or vals.get('gxtkAppState')
    if not state:raise ValueError('monkeystate key not found')
    if state.startswith('#TWEAKS'):
        mark='#ENDTWEAKS'; end=state.find(mark)
        if end<0:raise ValueError('unterminated tweaks prefix')
        state=state[end+len(mark):].lstrip('\r\n')
    return state

def player_record(path,slot=0):
    state=state_xml(path); rec=state.split(';'); base=slot*5
    if len(rec)<=base+1:raise ValueError('player record missing')
    return rec[base+1].rstrip('\r\n')

def _tokens(record):return record.split(',')

def verify_snapshots(pre_path,post_path,restart_path,flow_text):
    pre=player_record(pre_path); post=player_record(post_path); restart=player_record(restart_path)
    pt,qt,rt=map(_tokens,(pre,post,restart)); checks=[]
    def ck(ok,label):checks.append({'ok':bool(ok),'label':label})
    for key,text in SENTINEL_TEXT.items():
        label=LABELS[key]
        ck(text not in pt,f'pre-save lacks {key} sentinel')
        ck(text in qt,label)
        ck(text in rt,label.replace('post contains','restart contains'))
    ck(pre!=post,'TEST-ONLY mutation changes serialized player record')
    ck(bool(re.search(r'SAVE CAREER|SaveCareer|SaveState',flow_text,re.I)),'runtime flow contains stock Career save evidence')
    ck(bool(re.search(r'LoadCareer saveslot:\s*0',flow_text,re.I)),'runtime flow contains stock slot-0 reload evidence')
    h=lambda s:hashlib.sha256(s.encode()).hexdigest()
    return {'passed':all(x['ok'] for x in checks),'checks':checks,'pre_player_sha256':h(pre),'post_player_sha256':h(post),'restart_player_sha256':h(restart),'sentinels':SENTINEL_TEXT}

def main():
    if len(sys.argv)!=5:raise SystemExit('usage: verify_stage7_persistence_runtime.py PRE POST RESTART FLOW')
    pre,post,restart,flow_path=sys.argv[1:]
    result=verify_snapshots(pre,post,restart,Path(flow_path).read_text(encoding='utf-8',errors='replace'))
    lines=['NSS REBORN — ETAP 7 PERSISTENCE RUNTIME VERIFICATION']
    for i,c in enumerate(result['checks'],1):lines.append(f"{'PASS' if c['ok'] else 'FAIL'} {i}/{len(result['checks'])} {c['label']}")
    lines.append(f"PASS_COUNT={sum(c['ok'] for c in result['checks'])}/{len(result['checks'])}")
    lines.append('VERDICT='+('STAGE7_PERSISTENCE_RUNTIME_PASS' if result['passed'] else 'STAGE7_PERSISTENCE_RUNTIME_FAIL'))
    print('\n'.join(lines))
    if not result['passed']:raise SystemExit(1)

if __name__=='__main__':main()
