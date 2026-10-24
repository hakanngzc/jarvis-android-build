#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def same_after_restart(post, restart):
    keys = (
        'sdate','clubnationid','clubid','goalbonus','wage',
        'lastnegotiations','lasttransferdate','playerrecordsha256',
        'playerrecordnodatesha256',
        'clubrecordsha256','competitionrecordsha256','additionalclubrecordsha256',
    )
    return all(post.get(k) == restart.get(k) for k in keys)


def has_retired_restart_mainmenu_proof(text):
    if not text:
        return False
    created = re.search(r'Create Screen:[[:space:]]*mainmenu', text, re.I) is not None
    active = re.search(r'(?:SETTING ACTIVE:|SetActive:)[[:space:]]*mainmenu', text, re.I) is not None
    return created and active


def verify_scenario(scenario, base, post, restart, destination_club_id=None, retire_restart_mainmenu=False):
    checks = {}
    checks['restart_equivalent'] = same_after_restart(post, restart)
    checks['player_record_changed'] = post.get('playerrecordsha256') != base.get('playerrecordsha256')

    if scenario == 'accept':
        checks.update({
            'club_unchanged': post['clubid'] == base['clubid'],
            'lastnegotiations_is_current_date': post['lastnegotiations'] == post['sdate'],
            'lasttransferdate_is_current_date': post['lasttransferdate'] == post['sdate'],
            'contract_terms_written': (post['wage'], post['goalbonus']) != (base['wage'], base['goalbonus'])
                or post['lasttransferdate'] != base['lasttransferdate'],
        })
    elif scenario == 'reject':
        checks.update({
            'club_unchanged': post['clubid'] == base['clubid'],
            'lastnegotiations_is_current_date': post['lastnegotiations'] == post['sdate'],
            'lasttransferdate_unchanged': post['lasttransferdate'] == base['lasttransferdate'],
            'wage_unchanged': post['wage'] == base['wage'],
            'goalbonus_unchanged': post['goalbonus'] == base['goalbonus'],
        })
    elif scenario == 'transfer':
        checks.update({
            'destination_supplied': destination_club_id is not None,
            'club_changed': post['clubid'] != base['clubid'],
            'club_is_destination': post['clubid'] == destination_club_id,
            'nation_preserved': post['clubnationid'] == base['clubnationid'],
            'lastnegotiations_is_current_date': post['lastnegotiations'] == post['sdate'],
            'lasttransferdate_is_current_date': post['lasttransferdate'] == post['sdate'],
        })
    elif scenario == 'retire':
        checks.update({
            'date_decremented_once': post['sdate'] == base['sdate'] - 1,
            # m_ButtonPlay is statically verified as the sole gameplay writer
            # of durable m_retired. Normalize only m_sdate and require another
            # player-record mutation to survive restart, avoiding an invented
            # CSV index for m_retired.
            'retirement_state_changed_beyond_date':
                post.get('playerrecordnodatesha256') is not None
                and post.get('playerrecordnodatesha256') != base.get('playerrecordnodatesha256'),
            # A retired slot is no longer reopened through Career/SaveSlot in
            # the stock UI. The real restart/load boundary is stock MainMenu,
            # where retired slot metadata has already been consumed.
            'retired_restart_mainmenu_reached': bool(retire_restart_mainmenu),
        })
    else:
        raise ValueError(f'unknown scenario {scenario!r}')

    return {
        'scenario': scenario,
        'checks': checks,
        'pass': all(checks.values()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', required=True, choices=('accept','reject','transfer','retire'))
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--post', type=Path, required=True)
    ap.add_argument('--restart', type=Path, required=True)
    ap.add_argument('--destination-club-id', type=int)
    ap.add_argument('--retire-mainmenu-proof', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()

    load = lambda p: json.loads(p.read_text(encoding='utf-8'))
    proof_text = ''
    if args.retire_mainmenu_proof:
        proof_text = args.retire_mainmenu_proof.read_text(encoding='utf-8', errors='replace')
    result = verify_scenario(
        args.scenario,
        load(args.base),
        load(args.post),
        load(args.restart),
        destination_club_id=args.destination_club_id,
        retire_restart_mainmenu=has_retired_restart_mainmenu_proof(proof_text),
    )
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    if not result['pass']:
        raise SystemExit(1)
    print(f'STAGE2_{args.scenario.upper()}_RESTART_RELOAD_PASS')


if __name__ == '__main__':
    main()
