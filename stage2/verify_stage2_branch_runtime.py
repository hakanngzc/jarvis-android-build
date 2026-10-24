#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from stage2_checkpoint import parse_monkey_state

PERSIST_RUNTIME_KEYS = (
    'clubid', 'clubnationid', 'wage', 'goalbonus', 'assistbonus',
    'lastnegotiations', 'lasttransferdate', 'retired', 'sdate',
)
SAVE_HASH_KEYS = (
    'playerrecordsha256', 'clubrecordsha256',
    'competitionrecordsha256', 'additionalclubrecordsha256',
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('scenario', choices=['accept', 'reject', 'transfer', 'retirement'])
    ap.add_argument('baseline_xml', type=Path)
    ap.add_argument('post_xml', type=Path)
    ap.add_argument('reload_xml', type=Path)
    ap.add_argument('scenario_json', type=Path)
    ap.add_argument('reload_runtime_json', type=Path)
    args = ap.parse_args()

    baseline = parse_monkey_state(args.baseline_xml)
    post = parse_monkey_state(args.post_xml)
    reload_save = parse_monkey_state(args.reload_xml)
    scenario = json.loads(args.scenario_json.read_text(encoding='utf-8'))
    reload_runtime = json.loads(args.reload_runtime_json.read_text(encoding='utf-8'))
    if not scenario.get('ok'):
        raise SystemExit(f"scenario probe failed: {scenario.get('error')}")
    if not reload_runtime.get('ok'):
        raise SystemExit(f"reload runtime probe failed: {reload_runtime.get('error')}")

    before = scenario['before']
    after = scenario['after']
    reloaded = {k: reload_runtime[k] for k in PERSIST_RUNTIME_KEYS}
    checks: list[tuple[bool, str]] = []

    def ck(ok, label):
        checks.append((bool(ok), label))

    ck(args.scenario == scenario.get('scenario'), 'scenario identity')
    ck(scenario.get('thread_name', '').startswith('GLThread'), 'scenario executed on GL renderer thread')
    ck(before['clubid'] == baseline['clubid'], 'runtime baseline club matches save')
    ck(before['wage'] == baseline['wage'], 'runtime baseline wage matches save')
    ck(before['goalbonus'] == baseline['goalbonus'], 'runtime baseline goal bonus matches save')
    ck(before['lastnegotiations'] == baseline['lastnegotiations'], 'runtime baseline last negotiations matches save')
    ck(before['lasttransferdate'] == baseline['lasttransferdate'], 'runtime baseline transfer date matches save')
    ck(before['sdate'] == baseline['sdate'], 'runtime baseline date matches save')

    for key in SAVE_HASH_KEYS:
        ck(post[key] == reload_save[key], f'{key} survives restart/load')
    for key in ('clubid', 'clubnationid', 'wage', 'goalbonus', 'lastnegotiations', 'lasttransferdate', 'sdate'):
        ck(post[key] == reload_save[key], f'save field {key} survives restart/load')
    for key in PERSIST_RUNTIME_KEYS:
        ck(after[key] == reloaded[key], f'runtime field {key} survives restart/load')

    sent = scenario['sentinels']
    if args.scenario == 'accept':
        ck(after['clubid'] == before['clubid'], 'accept keeps current club')
        ck(after['wage'] == sent['wage'], 'accept writes sentinel wage')
        ck(after['goalbonus'] == sent['goalbonus'], 'accept writes sentinel goal bonus')
        ck(after['assistbonus'] == sent['assistbonus'], 'accept writes sentinel assist bonus')
        ck(after['lastnegotiations'] == before['sdate'], 'accept writes last negotiations date')
        ck(after['lasttransferdate'] == before['sdate'], 'accept writes contract transfer-date field')
        ck(post['wage'] == sent['wage'] and post['goalbonus'] == sent['goalbonus'], 'accepted contract reached save record')
    elif args.scenario == 'reject':
        ck(after['clubid'] == before['clubid'], 'reject keeps current club')
        ck(after['wage'] == before['wage'], 'reject keeps wage')
        ck(after['goalbonus'] == before['goalbonus'], 'reject keeps goal bonus')
        ck(after['assistbonus'] == before['assistbonus'], 'reject keeps assist bonus')
        ck(after['lastnegotiations'] == before['sdate'], 'reject writes last negotiations date for same-club offer')
        ck(after['lasttransferdate'] == before['lasttransferdate'], 'reject keeps last transfer date')
        ck(post['lastnegotiations'] == before['sdate'], 'rejected contract reached save record')
    elif args.scenario == 'transfer':
        ck(after['clubid'] == scenario['target_clubid'], 'transfer selects intended target club')
        ck(after['clubid'] != before['clubid'], 'transfer changes club')
        ck(after['wage'] == sent['wage'], 'transfer writes sentinel wage')
        ck(after['goalbonus'] == sent['goalbonus'], 'transfer writes sentinel goal bonus')
        ck(after['assistbonus'] == sent['assistbonus'], 'transfer writes sentinel assist bonus')
        ck(after['lastnegotiations'] == before['sdate'], 'transfer writes last negotiations date')
        ck(after['lasttransferdate'] == before['sdate'], 'transfer writes last transfer date')
        ck(post['clubid'] == scenario['target_clubid'], 'transferred club reached save record')
        ck(post['wage'] == sent['wage'] and post['goalbonus'] == sent['goalbonus'], 'transfer contract reached save record')
    else:
        ck(before['retired'] != sent['retired'], 'retirement sentinel differs from baseline')
        ck(after['retired'] == sent['retired'], 'retirement writer copies m_score[0] to m_retired')
        ck(after['sdate'] == before['sdate'] - 1, 'retirement writer decrements sdate before save')
        ck(post['sdate'] == before['sdate'] - 1, 'retirement date mutation reached save record')
        ck(post['playerrecordsha256'] != baseline['playerrecordsha256'], 'retirement changes durable player record')

    lines = [f'NSS REBORN — STAGE2 {args.scenario.upper()} RUNTIME VERIFICATION']
    for i, (ok, label) in enumerate(checks, 1):
        lines.append(f"{'PASS' if ok else 'FAIL'} {i}/{len(checks)} {label}")
    lines.append(f'PASS_COUNT={sum(ok for ok, _ in checks)}/{len(checks)}')
    verdict = all(ok for ok, _ in checks)
    lines.append('VERDICT=' + (f'STAGE2_{args.scenario.upper()}_PASS' if verdict else f'STAGE2_{args.scenario.upper()}_FAIL'))
    print('\n'.join(lines))
    if not verdict:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
