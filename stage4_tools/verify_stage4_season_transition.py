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
    out.update(playerrecordsha256=h(player),clubrecordsha256=h(rec[base+2]),competitionrecordsha256=h(rec[base+3]),additionalclubrecordsha256=h(rec[base+4]))
    return out

def main():
    if len(sys.argv)!=6: raise SystemExit('usage: verify_stage4_season_transition.py PRE SEEDED POST RESTART FLOW')
    pre,seeded,post,restart,flow_path=sys.argv[1:]
    a,b,c,d=map(checkpoint,(pre,seeded,post,restart))
    flow=Path(flow_path).read_text(encoding='utf-8',errors='replace')
    checks=[]
    def ck(ok,label): checks.append((bool(ok),label))
    ck(b['sdate']==365,'test trigger reaches year-2 boundary sdate=365')
    ck(b['seasonapps']==7,'pre-reset sentinel seasonApps=7 persisted by p_NewSeason save')
    ck(c['seasonapps']==0,'stock p_ResetSeasonStats clears seasonApps')
    ck(d['seasonapps']==0,'seasonApps reset survives restart/load')
    ck(c['sdate']>=365,'post-rollover Career remains in new season')
    ck(c['sdate']>=b['sdate'],'new-season setup does not move Career date backwards')
    ck(b['competitionrecordsha256']!=c['competitionrecordsha256'],'competition block rebuilt after NewSeasonSetUp1')
    ck(c['competitionrecordsha256']==d['competitionrecordsha256'],'rebuilt competition block survives restart')
    ck(c['clubrecordsha256']==d['clubrecordsha256'],'club block survives restart')
    ck(c['playerrecordsha256']==d['playerrecordsha256'],'player block survives restart')
    ck(c['clubid']==d['clubid'],'club identity survives restart')
    ck(bool(re.search(r'NewSeason',flow,re.I)),'runtime flow contains NewSeason evidence')
    ck(bool(re.search(r'LoadCareer saveslot:\s*0',flow,re.I)),'restart flow reloads slot 0')
    ck(bool(re.search(r'(Create Screen:|SETTING ACTIVE:|SetActive:)\s*gamemenu',flow,re.I)),'rollover returns to GameMenu')
    lines=['NSS REBORN — ETAP 4 SEASON TRANSITION RUNTIME VERIFICATION']
    for i,(ok,label) in enumerate(checks,1): lines.append(f"{'PASS' if ok else 'FAIL'} {i}/{len(checks)} {label}")
    lines.append(f"pre_sdate={a['sdate']} seeded_sdate={b['sdate']} post_sdate={c['sdate']} restart_sdate={d['sdate']}")
    lines.append(f"seeded_seasonApps={b['seasonapps']} post_seasonApps={c['seasonapps']} restart_seasonApps={d['seasonapps']}")
    lines.append(f"PASS_COUNT={sum(ok for ok,_ in checks)}/{len(checks)}")
    lines.append('VERDICT='+('STAGE4_SEASON_RUNTIME_PASS' if all(ok for ok,_ in checks) else 'STAGE4_SEASON_RUNTIME_FAIL'))
    print('\n'.join(lines))
    if not all(ok for ok,_ in checks): raise SystemExit(1)
if __name__=='__main__':main()
