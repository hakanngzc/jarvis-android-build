#!/usr/bin/env python3
from __future__ import annotations
import hashlib,re,sys,xml.etree.ElementTree as ET
from pathlib import Path

FIELD_INDEX={'sdate':0,'clubnationid':1,'clubid':2,'careerapps':13,'seasonapps':23}

def state_xml(path):
    root=ET.fromstring(Path(path).read_text(encoding='utf-8'))
    vals={n.attrib.get('name'):(n.text or '') for n in root.findall('string')}
    state=vals.get('.monkeystate') or vals.get('gxtkAppState')
    if not state: raise ValueError('monkeystate key not found')
    if state.startswith('#TWEAKS'):
        mark='#ENDTWEAKS'; end=state.find(mark)
        if end<0: raise ValueError('unterminated tweaks prefix')
        state=state[end+len(mark):].lstrip('\r\n')
    return state

def checkpoint(path,slot=0):
    state=state_xml(path); rec=state.split(';'); base=slot*5
    player=rec[base+1]; tok=player.rstrip('\r\n').split(',')
    out={k:int(tok[i]) for k,i in FIELD_INDEX.items()}
    h=lambda s:hashlib.sha256(s.encode()).hexdigest()
    out.update(
        playerrecordsha256=h(player),
        clubrecordsha256=h(rec[base+2]),
        competitionrecordsha256=h(rec[base+3]),
        additionalclubrecordsha256=h(rec[base+4]),
    )
    return out

def main():
    if len(sys.argv)!=5:
        raise SystemExit('usage: verify_stage4_season_transition.py PRE POST RESTART FLOW')
    pre,post,restart,flow_path=sys.argv[1:]
    a,c,d=map(checkpoint,(pre,post,restart))
    flow=Path(flow_path).read_text(encoding='utf-8',errors='replace')
    checks=[]
    def ck(ok,label): checks.append((bool(ok),label))

    ck(c['sdate']>=365,'post-rollover Career reaches the new-season date range')
    ck(c['sdate']>a['sdate'],'season rollover advances Career date')
    ck(c['seasonapps']==0,'stock NewSeasonSetUp3 leaves seasonApps reset')
    ck(d['seasonapps']==0,'seasonApps reset survives restart/load')
    ck(a['competitionrecordsha256']!=c['competitionrecordsha256'],'competition block rebuilt during season rollover')
    ck(c['competitionrecordsha256']==d['competitionrecordsha256'],'rebuilt competition block survives restart')
    ck(c['clubrecordsha256']==d['clubrecordsha256'],'club block survives restart')
    ck(c['playerrecordsha256']==d['playerrecordsha256'],'player block survives restart')
    ck(c['additionalclubrecordsha256']==d['additionalclubrecordsha256'],'additional-club block survives restart')
    ck(c['clubid']==d['clubid'],'club identity survives restart')
    ck(c['clubnationid']==d['clubnationid'],'club nation identity survives restart')

    ck(bool(re.search(r'\bNewSeason\b',flow,re.I)),'runtime flow contains NewSeason evidence')
    ck(bool(re.search(r'CallFunc:\s*NewSeasonSetUp1',flow,re.I)),'runtime executes NewSeasonSetUp1')
    ck(bool(re.search(r'CallFunc:\s*NewSeasonSetUp2',flow,re.I)),'runtime executes NewSeasonSetUp2')
    ck(bool(re.search(r'CallFunc:\s*NewSeasonSetUp3',flow,re.I)),'runtime executes NewSeasonSetUp3')
    ck(bool(re.search(r'CallFunc:\s*NewSeasonSetUp4',flow,re.I)),'runtime executes NewSeasonSetUp4')
    ck(bool(re.search(r'SAVE CAREER',flow,re.I)),'runtime executes stock Career save during rollover')
    ck(bool(re.search(r'New Season - Save',flow,re.I)),'runtime reaches stock final new-season save')
    ck(bool(re.search(r'LoadCareer saveslot:\s*0',flow,re.I)),'runtime reloads slot 0 during/after rollover')
    ck(bool(re.search(r'(Create Screen:|SETTING ACTIVE:|SetActive:)\s*gamemenu',flow,re.I)),'rollover returns to GameMenu')

    lines=['NSS REBORN — ETAP 4 SEASON TRANSITION RUNTIME VERIFICATION']
    for i,(ok,label) in enumerate(checks,1):
        lines.append(f"{'PASS' if ok else 'FAIL'} {i}/{len(checks)} {label}")
    lines.append(f"pre_sdate={a['sdate']} post_sdate={c['sdate']} restart_sdate={d['sdate']}")
    lines.append(f"pre_seasonApps={a['seasonapps']} post_seasonApps={c['seasonapps']} restart_seasonApps={d['seasonapps']}")
    lines.append(f"PASS_COUNT={sum(ok for ok,_ in checks)}/{len(checks)}")
    lines.append('VERDICT='+('STAGE4_SEASON_RUNTIME_PASS' if all(ok for ok,_ in checks) else 'STAGE4_SEASON_RUNTIME_FAIL'))
    print('\n'.join(lines))
    if not all(ok for ok,_ in checks): raise SystemExit(1)

if __name__=='__main__': main()
