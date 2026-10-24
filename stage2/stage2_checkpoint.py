#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path

FIELD_INDEX = {
    'sdate': 0,
    'clubnationid': 1,
    'clubid': 2,
    'fullname': 3,
    'shortname': 4,
    'careerapps': 13,
    'goalbonus': 33,
    'wage': 34,
    # Verified against real Stage2 runtime artifacts on NSS 4.31:
    # accept mutates 581/582, assist bonus is 898, retirement flag is 910.
    'lastnegotiations': 581,
    'lasttransferdate': 582,
    'assistbonus': 898,
    'retired': 910,
}


def parse_monkey_state(path: Path, slot: int = 0) -> dict:
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

    records = state.split(';')
    base = slot * 5
    if len(records) <= base + 4:
        raise ValueError(f'save slot {slot} records missing in {path}')
    player = records[base + 1]
    tokens = player.rstrip('\r\n').split(',')
    out = {}
    for key, idx in FIELD_INDEX.items():
        if idx >= len(tokens):
            raise ValueError(f'{key} index {idx} outside player record ({len(tokens)} tokens)')
        out[key] = tokens[idx] if key in ('fullname', 'shortname') else int(tokens[idx])

    digest = lambda text: hashlib.sha256(text.encode('utf-8')).hexdigest()
    out.update(
        playerrecordsha256=digest(player),
        clubrecordsha256=digest(records[base + 2]),
        competitionrecordsha256=digest(records[base + 3]),
        additionalclubrecordsha256=digest(records[base + 4]),
        player_token_count=len(tokens),
    )
    return out
