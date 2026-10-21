#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

from stage2_checkpoint import extract_checkpoint
from verify_stage3_minimal import competition, ident, parse, state_xml, club_slots


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit('usage: verify_stage3_simulation.py PRE_XML POST_XML RESTART_XML FLOW')
    pre, post, restart, flow_path = sys.argv[1:]
    a, b, c = state_xml(pre), state_xml(post), state_xml(restart)
    cp0 = extract_checkpoint(a, 0)
    cp1 = extract_checkpoint(b, 0)
    cp2 = extract_checkpoint(c, 0)
    comp0 = competition(a)
    flow = Path(flow_path).read_text(encoding='utf-8', errors='replace')

    dates = {int(v) for v in re.findall(r'SetUpFixture:\s*(-?\d+)', flow, re.I)}
    if len(dates) != 1:
        raise ValueError(f'expected one SetUpFixture date, found {sorted(dates)}')
    sdate = next(iter(dates))
    club = int(cp0['clubid'])
    slots = club_slots(comp0, club)
    if not slots:
        raise ValueError(f'club {club} not found in competition rosters')

    before = []
    for compid, slot in slots:
        before.extend(
            (f, slot)
            for f in parse(comp0)
            if f['sdate'] == sdate and f['compid'] == compid and f['result'] == 0 and slot in (f['home'], f['away'])
        )
    if len(before) != 1:
        raise ValueError(f'expected one unresolved selected fixture, found {len(before)} from slots {slots}')
    bf, clubslot = before[0]
    key = ident(bf)
    after = [f for f in parse(competition(b)) if ident(f) == key]
    again = [f for f in parse(competition(c)) if ident(f) == key]
    if len(after) != 1 or len(again) != 1:
        raise ValueError('selected fixture identity not unique after simulated match/restart')
    af, rf = after[0], again[0]

    checks = []
    def ck(ok, label):
        checks.append((bool(ok), label))

    ck(cp0['competitionrecordsha256'] != cp1['competitionrecordsha256'], 'competition block changed after simulated match')
    ck(cp1['competitionrecordsha256'] == cp2['competitionrecordsha256'], 'competition block persists restart')
    ck(cp1['clubrecordsha256'] == cp2['clubrecordsha256'], 'club block persists restart')
    ck(cp1['playerrecordsha256'] == cp2['playerrecordsha256'], 'player block persists restart')
    ck(cp1['sdate'] == cp2['sdate'], 'career date persists restart')
    ck(af['result'] != 0, 'simulated selected fixture resolved')
    ck(af['score1'] >= 0 and af['score2'] >= 0, 'simulated selected fixture has concrete score')
    persisted = ('result', 'resulttype', 'score1', 'score2', 'penscore1', 'penscore2')
    ck(all(af[k] == rf[k] for k in persisted), 'simulated fixture result persists restart')

    required = [
        r'HitGadget:\s*match\.autoplayAverage',
        r'SIMULATING MATCH',
        r'matchstats',
        r'MyMatchPlayed',
        r'PlayToDate',
        r'LoadCareer saveslot: 0',
    ]
    for pat in required:
        ck(bool(re.search(pat, flow, re.I)), f'flow contains {pat}')

    lines = ['NSS REBORN — ETAP 3 STOCK SIMULATION RUNTIME VERIFICATION']
    for i, (ok, label) in enumerate(checks, 1):
        lines.append(f"{'PASS' if ok else 'FAIL'} {i}/{len(checks)} {label}")
    lines.append(
        f"selected_fixture=date:{sdate} club:{club} comp:{af['compid']} slot:{clubslot} "
        f"home:{af['home']} away:{af['away']} score:{af['score1']}-{af['score2']} "
        f"result:{af['result']} resulttype:{af['resulttype']}"
    )
    lines.append(f"PASS_COUNT={sum(x for x, _ in checks)}/{len(checks)}")
    lines.append('VERDICT=' + ('STAGE3_SIMULATION_GATE_PASS' if all(x for x, _ in checks) else 'STAGE3_SIMULATION_GATE_FAIL'))
    report = '\n'.join(lines) + '\n'
    print(report, end='')
    return 0 if all(x for x, _ in checks) else 1


if __name__ == '__main__':
    raise SystemExit(main())
