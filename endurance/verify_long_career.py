#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

FIELD_INDEX = {
    'sdate': 0,
    'clubnationid': 1,
    'clubid': 2,
    'careerapps': 13,
    'seasonapps': 23,
}
BLOCKS = ('playerrecordsha256', 'clubrecordsha256', 'competitionrecordsha256', 'additionalclubrecordsha256')


def checkpoint(path: Path, slot: int = 0) -> dict:
    root = ET.fromstring(path.read_text(encoding='utf-8'))
    vals = {n.attrib.get('name'): (n.text or '') for n in root.findall('string')}
    state = vals.get('.monkeystate') or vals.get('gxtkAppState')
    if not state:
        raise ValueError(f'monkeystate key not found in {path}')
    if state.startswith('#TWEAKS'):
        mark = '#ENDTWEAKS'
        end = state.find(mark)
        if end < 0:
            raise ValueError('unterminated tweaks prefix')
        state = state[end + len(mark):].lstrip('\r\n')
    rec = state.split(';')
    base = slot * 5
    player = rec[base + 1]
    tok = player.rstrip('\r\n').split(',')
    out = {k: int(tok[i]) for k, i in FIELD_INDEX.items()}
    digest = lambda s: hashlib.sha256(s.encode('utf-8')).hexdigest()
    out.update(
        playerrecordsha256=digest(player),
        clubrecordsha256=digest(rec[base + 2]),
        competitionrecordsha256=digest(rec[base + 3]),
        additionalclubrecordsha256=digest(rec[base + 4]),
    )
    return out


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit('usage: verify_long_career.py EVIDENCE_DIR SEASON_COUNT')
    root = Path(sys.argv[1])
    count = int(sys.argv[2])
    if count < 2:
        raise SystemExit('SEASON_COUNT must be at least 2')

    previous = checkpoint(root / 'season-0-baseline-MonkeyGame.xml')
    checks: list[tuple[bool, str]] = []
    rows = []

    def ck(ok, label):
        checks.append((bool(ok), label))

    for season in range(1, count + 1):
        post = checkpoint(root / f'season-{season}-post-MonkeyGame.xml')
        reload = checkpoint(root / f'season-{season}-reload-MonkeyGame.xml')
        rows.append((season, previous['sdate'], post['sdate'], reload['sdate']))

        ck(post['sdate'] >= previous['sdate'] + 365,
           f'season {season}: Career date advances by at least one full season')
        ck(post['sdate'] == reload['sdate'],
           f'season {season}: Career date survives restart/load')
        ck(post['seasonapps'] == 0 and reload['seasonapps'] == 0,
           f'season {season}: stock seasonApps reset survives restart/load')
        ck(previous['competitionrecordsha256'] != post['competitionrecordsha256'],
           f'season {season}: competition block is rebuilt')
        for key in BLOCKS:
            ck(post[key] == reload[key], f'season {season}: {key} survives restart/load')
        ck(post['clubid'] == reload['clubid'], f'season {season}: club identity survives restart/load')
        ck(post['clubnationid'] == reload['clubnationid'], f'season {season}: club nation survives restart/load')
        previous = post

    lines = ['NSS REBORN — LONG CAREER ENDURANCE VERIFICATION']
    for i, (ok, label) in enumerate(checks, 1):
        lines.append(f"{'PASS' if ok else 'FAIL'} {i}/{len(checks)} {label}")
    for season, before, post, reload in rows:
        lines.append(f'season_{season}: before_sdate={before} post_sdate={post} reload_sdate={reload}')
    lines.append(f'PASS_COUNT={sum(ok for ok, _ in checks)}/{len(checks)}')
    lines.append('VERDICT=' + ('LONG_CAREER_ENDURANCE_PASS' if all(ok for ok, _ in checks) else 'LONG_CAREER_ENDURANCE_FAIL'))
    print('\n'.join(lines))
    if not all(ok for ok, _ in checks):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
