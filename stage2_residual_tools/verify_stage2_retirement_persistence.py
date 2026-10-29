#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

CHECKPOINT_KEYS = (
    'sdate', 'clubnationid', 'clubid', 'goalbonus', 'wage',
    'lastnegotiations', 'lasttransferdate', 'playerrecordsha256',
    'clubrecordsha256', 'competitionrecordsha256', 'additionalclubrecordsha256',
)


def same_after_restart(post: dict, restart: dict) -> bool:
    return all(post.get(key) == restart.get(key) for key in CHECKPOINT_KEYS)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(base: dict, post: dict, restart: dict, post_xml: bytes, restart_xml: bytes, flow: str) -> dict:
    checks = {
        'date_decremented_once': post.get('sdate') == base.get('sdate', 0) - 1,
        'restart_equivalent': same_after_restart(post, restart),
        'player_record_changed': post.get('playerrecordsha256') != base.get('playerrecordsha256'),
        'player_record_persisted': restart.get('playerrecordsha256') == post.get('playerrecordsha256'),
        'raw_save_nonempty': bool(post_xml) and bool(restart_xml),
        'raw_save_byte_identical': post_xml == restart_xml,
        'retirement_screen_marker': re.search(r'Create Screen:\s*retirement', flow, flags=re.IGNORECASE) is not None,
        'quick_save_marker': 'QUICK SAVE' in flow,
        'loadcareer_marker': 'LoadCareer saveslot: 0' in flow,
        'retired_marker': '>>>> RETIRED' in flow,
    }
    passed = all(checks.values())
    return {
        'verdict': 'STAGE2_RETIREMENT_PERSISTENCE_PASS' if passed else 'STAGE2_RETIREMENT_PERSISTENCE_FAIL',
        'checks': checks,
        'evidence': {
            'post_xml_sha256': _sha256(post_xml),
            'restart_xml_sha256': _sha256(restart_xml),
            'post_xml_size': len(post_xml),
            'restart_xml_size': len(restart_xml),
            'sdate_pre': base.get('sdate'),
            'sdate_post': post.get('sdate'),
            'sdate_restart': restart.get('sdate'),
            'playerrecordsha256_pre': base.get('playerrecordsha256'),
            'playerrecordsha256_post': post.get('playerrecordsha256'),
            'playerrecordsha256_restart': restart.get('playerrecordsha256'),
        },
        'pass': passed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--post', type=Path, required=True)
    parser.add_argument('--restart', type=Path, required=True)
    parser.add_argument('--post-xml', type=Path, required=True)
    parser.add_argument('--restart-xml', type=Path, required=True)
    parser.add_argument('--flow', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    load_json = lambda path: json.loads(path.read_text(encoding='utf-8'))
    result = verify(
        load_json(args.base),
        load_json(args.post),
        load_json(args.restart),
        args.post_xml.read_bytes(),
        args.restart_xml.read_bytes(),
        args.flow.read_text(encoding='utf-8', errors='replace'),
    )
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))
    if not result['pass']:
        raise SystemExit(1)
    print('STAGE2_RETIREMENT_PERSISTENCE_PASS')


if __name__ == '__main__':
    main()
