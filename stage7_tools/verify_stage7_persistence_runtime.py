#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, sys, xml.etree.ElementTree as ET
from pathlib import Path
try:
    from .patch_stage7_persistence_probe import SENTINELS
except ImportError:
    from patch_stage7_persistence_probe import SENTINELS

def state_xml(path):
    raw=Path(path).read_bytes(); root=ET.fromstring(raw.decode('utf-8'))
    vals={n.attrib.get('name'):(n.text or '') for n in root.findall('string')}
    state=vals.get('.monkeystate') or vals.get('gxtkAppState')
    if not state: raise ValueError('monkeystate key not found')
    if state.startswith('#TWEAKS'):
        mark='#ENDTWEAKS'; end=state.find(mark)
        if end<0:raise ValueError('unterminated tweaks prefix')
        state=state[end+len(mark):].lstrip('\r\n')
    return raw,state

def player_tokens(path,slot=0):
    raw,state=state_xml(path); rec=state.split(';'); base=slot*5
    if len(rec)<=base+1:raise ValueError('slot player record missing')
    player=rec[base+1]; return raw,player.rstrip('\r\n').split(',')

def verify_checkpoints(pre_path,mutated_path,update_path,reloaded_path,flow):
    pre_raw,pre=player_tokens(pre_path); mut_raw,mut=player_tokens(mutated_path); upd_raw,upd=player_tokens(update_path); rel_raw,rel=player_tokens(reloaded_path)
    errors=[]; sentinel_indexes={}
    if mut_raw!=upd_raw: errors.append('package update changed saved state before reload')
    if len(pre)!=len(mut): errors.append(f'player token length changed pre={len(pre)} mutated={len(mut)}')
    if len(mut)!=len(rel): errors.append(f'player token length changed mutated={len(mut)} reloaded={len(rel)}')
    lim=min(len(pre),len(mut),len(rel))
    changed=[i for i in range(min(len(pre),len(mut))) if pre[i]!=mut[i]]
    for label,value in SENTINELS.items():
        sval=str(value)
        candidates=[i for i in changed if i<lim and mut[i]==sval]
        if not candidates:
            errors.append(f'{label}: sentinel {value} not found in mutation-changed player tokens')
            continue
        survivors=[i for i in candidates if rel[i]==sval]
        if not survivors:
            errors.append(f'{label}: reload lost sentinel {value} at token(s) {candidates}')
            continue
        sentinel_indexes[label]=survivors[0]
    if len(sentinel_indexes)!=len(SENTINELS): errors.append(f'sentinel coverage {len(sentinel_indexes)}/{len(SENTINELS)}')
    if not re.search(r'LoadCareer saveslot:\s*0',flow,re.I):errors.append('runtime flow missing stock LoadCareer slot0')
    if not re.search(r'(Create Screen:|SETTING ACTIVE:|SetActive:)\s*gamemenu',flow,re.I):errors.append('runtime flow missing GameMenu after reload')
    if len(re.findall(r'SAVE CAREER|SaveCareer|SaveState',flow,re.I))<2:errors.append('runtime flow missing two stock save events')
    return {
        'ok':not errors,'errors':errors,'sentinel_token_indexes':sentinel_indexes,'changed_token_count':len(changed),
        'pre_sha256':hashlib.sha256(pre_raw).hexdigest(),'mutated_sha256':hashlib.sha256(mut_raw).hexdigest(),
        'update_sha256':hashlib.sha256(upd_raw).hexdigest(),'reloaded_sha256':hashlib.sha256(rel_raw).hexdigest(),
    }

def main():
    if len(sys.argv)!=6:raise SystemExit('usage: verify_stage7_persistence_runtime.py PRE MUTATED AFTER_UPDATE RELOADED FLOW')
    flow=Path(sys.argv[5]).read_text(encoding='utf-8',errors='replace')
    result=verify_checkpoints(*sys.argv[1:5],flow)
    print('NSS REBORN — ETAP 7 REPRESENTATIVE PERSISTENCE RUNTIME VERIFICATION')
    for label,value in SENTINELS.items():
        idx=result['sentinel_token_indexes'].get(label)
        print(('PASS' if idx is not None else 'FAIL')+f' {label}={value} token={idx}')
    print(f"changed_token_count={result['changed_token_count']}")
    print(f"update_preserved_raw_save={result['mutated_sha256']==result['update_sha256']}")
    for e in result['errors']:print('FAIL '+e)
    print('VERDICT='+('STAGE7_REPRESENTATIVE_RUNTIME_PASS' if result['ok'] else 'STAGE7_REPRESENTATIVE_RUNTIME_FAIL'))
    if not result['ok']:raise SystemExit(1)
if __name__=='__main__':main()
