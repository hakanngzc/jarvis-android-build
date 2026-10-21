#!/usr/bin/env python3
from __future__ import annotations
import re,sys
from pathlib import Path
from stage2_checkpoint import extract_checkpoint, extract_monkeystate_from_prefs_xml, strip_tweaks_prefix

FIXTURE_RE=re.compile(r'(?<![0-9/])(-?\d+(?:/-?\d+){14,15})\?')
SECTION_RE=re.compile(r'@(\d+),(.+?)(?=@\d+,|$)',re.S)
FIELDS=('sdate','matchtype','round','groupno','leg','home','away','result','resulttype','score1','score2','penscore1','penscore2','level','compid','randno')
IDENTITY=('sdate','matchtype','round','groupno','leg','home','away','level','compid','randno')

def competition(state,slot=0):
    records=strip_tweaks_prefix(state).split(';'); return records[slot*5+3]
def parse(record):
    out=[]
    for m in FIXTURE_RE.finditer(record):
        vals=[int(v) for v in m.group(1).split('/')]
        if len(vals)==15: vals.append(None)
        if len(vals)==16: out.append(dict(zip(FIELDS,vals)))
    return out
def ident(f): return tuple(f[k] for k in IDENTITY)
def state_xml(p): return extract_monkeystate_from_prefs_xml(Path(p).read_text(encoding='utf-8'))

def club_slots(record,clubid):
    out=[]
    for m in SECTION_RE.finditer(record):
        compid=int(m.group(1)); body=m.group(2)
        roster=body.split('?*,',1)[0]
        for entry in roster.split('?'):
            parts=entry.split('/')
            if len(parts)>=2 and parts[0].isdigit() and parts[1].isdigit() and int(parts[1])==clubid:
                out.append((compid,int(parts[0])))
    return out

def main():
    if len(sys.argv)==5:
        pre,post,restart,flow_path=sys.argv[1:]
        report_path=None
    elif len(sys.argv)==6:
        pre,post,restart,flow_path,report_path=sys.argv[1:]
    else:
        raise SystemExit('usage: verify_stage3_minimal.py PRE_XML POST_XML RESTART_XML FLOW [REPORT]')
    a,b,c=state_xml(pre),state_xml(post),state_xml(restart)
    cp0=extract_checkpoint(a,0); cp1=extract_checkpoint(b,0); cp2=extract_checkpoint(c,0)
    comp0=competition(a)
    flow=Path(flow_path).read_text(encoding='utf-8',errors='replace')
    dates={int(v) for v in re.findall(r'SetUpFixture:\s*(-?\d+)',flow,re.I)}
    if len(dates)!=1: raise ValueError(f'expected one SetUpFixture date, found {sorted(dates)}')
    sdate=next(iter(dates)); club=int(cp0['clubid'])
    slots=club_slots(comp0,club)
    if not slots: raise ValueError(f'club {club} not found in competition rosters')
    fixtures=parse(comp0)
    before=[]
    for compid,slot in slots:
        before.extend((f,slot) for f in fixtures if f['sdate']==sdate and f['compid']==compid and f['result']==0 and slot in (f['home'],f['away']))
    if len(before)!=1: raise ValueError(f'expected one unresolved selected fixture, found {len(before)} from slots {slots}')
    bf,clubslot=before[0]
    key=ident(bf)
    after=[f for f in parse(competition(b)) if ident(f)==key]
    again=[f for f in parse(competition(c)) if ident(f)==key]
    if len(after)!=1 or len(again)!=1: raise ValueError('selected fixture identity not unique after match/restart')
    af,rf=after[0],again[0]
    checks=[]
    def ck(ok,label): checks.append((bool(ok),label))
    ck(cp0['competitionrecordsha256']!=cp1['competitionrecordsha256'],'competition block changed after match')
    ck(cp1['competitionrecordsha256']==cp2['competitionrecordsha256'],'competition block persists restart')
    ck(cp1['clubrecordsha256']==cp2['clubrecordsha256'],'club block persists restart')
    ck(cp1['playerrecordsha256']==cp2['playerrecordsha256'],'player block persists restart')
    ck(cp1['sdate']==cp2['sdate'],'career date persists restart')
    ck([af['score1'],af['score2']]==[1,0],'selected fixture score is 1-0')
    ck(af['result']!=0,'selected fixture resolved')
    persisted=('result','resulttype','score1','score2','penscore1','penscore2')
    ck(all(af[k]==rf[k] for k in persisted),'selected fixture result persists restart')
    required=[r'matchstats',r'MyMatchPlayed',r'PlayToDate',r'LoadCareer saveslot: 0']
    for pat in required: ck(bool(re.search(pat,flow,re.I)),f'flow contains {pat}')
    lines=['NSS REBORN — ETAP 3 MINIMAL RUNTIME VERIFICATION']
    for i,(ok,label) in enumerate(checks,1): lines.append(f"{'PASS' if ok else 'FAIL'} {i}/{len(checks)} {label}")
    lines.append(f"selected_fixture=date:{sdate} club:{club} comp:{af['compid']} slot:{clubslot} home:{af['home']} away:{af['away']} score:{af['score1']}-{af['score2']} result:{af['result']} resulttype:{af['resulttype']}")
    lines.append(f"PASS_COUNT={sum(x for x,_ in checks)}/{len(checks)}")
    lines.append('VERDICT='+('STAGE3_FULL_GATE_PASS' if all(x for x,_ in checks) else 'STAGE3_FULL_GATE_FAIL'))
    report='\n'.join(lines)+'\n'
    if report_path is not None:
        Path(report_path).write_text(report,encoding='utf-8')
    print(report,end='')
    if not all(x for x,_ in checks): raise SystemExit(1)
if __name__=='__main__': main()
