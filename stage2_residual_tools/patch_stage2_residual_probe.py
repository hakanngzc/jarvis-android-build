#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import re
import struct
import sys
import tempfile
import zlib
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'stage3_tools'))
from dex_inspect import Dex

UTILITY = 'Lcom/newstargames/newstarsoccer/bb_GSPlayerUtility;'
BB = 'Lcom/newstargames/newstarsoccer/bb_;'
PLAYER = 'Lcom/newstargames/newstarsoccer/c_TPlayer;'
CLUB = 'Lcom/newstargames/newstarsoccer/c_TClub;'
OFFER = 'Lcom/newstargames/newstarsoccer/c_TContractOffer;'
CONTRACT = 'Lcom/newstargames/newstarsoccer/c_TScreen_Contract;'
RETIREMENT = 'Lcom/newstargames/newstarsoccer/c_TScreen_Retirement;'
TARGET = 'g_GSPlayerPlayMatches'


def unique_index(items, owner, name, kind):
    hits = [i for i, item in enumerate(items) if item[0] == owner and item[1] == name]
    if len(hits) != 1:
        raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]


def proto_signature(d, mid):
    _owner, _name, proto_id = d.methods[mid]
    shorty_idx, ret_idx, params_off = struct.unpack_from('<III', d.b, d.proto_off + 12 * proto_id)
    params = []
    if params_off:
        count = struct.unpack_from('<I', d.b, params_off)[0]
        params = [d.types[struct.unpack_from('<H', d.b, params_off + 4 + 2 * i)[0]] for i in range(count)]
    return d.types[ret_idx], params, d.strings[shorty_idx]


def assert_proto(d, mid, ret, params, label):
    got_ret, got_params, shorty = proto_signature(d, mid)
    if (got_ret, got_params) != (ret, params):
        raise ValueError(f'unexpected {label} proto: {shorty} {got_ret} {got_params}')


def invoke_static(mid, regs):
    if len(regs) > 5 or any(r < 0 or r > 15 for r in regs):
        raise ValueError(f'invoke-static register set unsupported: {regs}')
    padded = list(regs) + [0] * (5 - len(regs))
    c, d, e, f, g = padded
    first = 0x71 | (g << 8) | (len(regs) << 12)
    third = c | (d << 4) | (e << 8) | (f << 12)
    return [first, mid, third]


def invoke_virtual(mid, regs):
    if not regs or len(regs) > 5 or any(r < 0 or r > 15 for r in regs):
        raise ValueError(f'invoke-virtual register set unsupported: {regs}')
    padded = list(regs) + [0] * (5 - len(regs))
    c, d, e, f, g = padded
    first = 0x6e | (g << 8) | (len(regs) << 12)
    third = c | (d << 4) | (e << 8) | (f << 12)
    return [first, mid, third]


def find_target(d):
    methods = [m for m in (d.class_methods(UTILITY) or []) if m[2][1] == TARGET and m[4]]
    if len(methods) != 1:
        raise ValueError(f'expected one {TARGET}, found {len(methods)}')
    _kind, mid, _mt, access, code = methods[0]
    if not (access & 0x8):
        raise ValueError(f'{TARGET} is not static')
    assert_proto(d, mid, 'V', [], TARGET)
    return mid, code


def verify_stock_chain(d):
    get_offer = unique_index(d.methods, OFFER, 'm_GetOffer', 'method')
    sign = unique_index(d.methods, OFFER, 'p_SignContract', 'method')
    setup = unique_index(d.methods, CONTRACT, 'm_SetUpScreen', 'method')
    accept = unique_index(d.methods, CONTRACT, 'm_ButtonAccept', 'method')
    reject = unique_index(d.methods, CONTRACT, 'm_ButtonReject', 'method')
    select = unique_index(d.methods, CLUB, 'm_SelectById', 'method')
    retire_setup = unique_index(d.methods, RETIREMENT, 'm_SetUpScreen', 'method')
    retire_play = unique_index(d.methods, RETIREMENT, 'm_ButtonPlay', 'method')

    assert_proto(d, get_offer, OFFER, [CLUB, 'Z', 'Z'], 'm_GetOffer')
    assert_proto(d, sign, 'I', [], 'p_SignContract')
    assert_proto(d, setup, 'I', [OFFER, 'Z'], 'Contract.m_SetUpScreen')
    assert_proto(d, accept, 'I', ['Z'], 'm_ButtonAccept')
    assert_proto(d, reject, 'I', [], 'm_ButtonReject')
    assert_proto(d, select, CLUB, ['I', 'Z'], 'm_SelectById')
    assert_proto(d, retire_setup, 'I', [], 'Retirement.m_SetUpScreen')
    assert_proto(d, retire_play, 'I', [], 'Retirement.m_ButtonPlay')

    accept_methods = [m for m in (d.class_methods(CONTRACT) or []) if m[2][1] == 'm_ButtonAccept' and m[4]]
    if len(accept_methods) != 1:
        raise ValueError('m_ButtonAccept body missing')
    _r, _i, _o, _t, _s, items = d.disasm(accept_methods[0][4])
    if not any(name == 'invoke-virtual' and f'method@{sign}' in args for _, name, args, _ in items):
        raise ValueError('stock m_ButtonAccept no longer invokes p_SignContract')

    return {
        'get_offer': get_offer,
        'sign': sign,
        'setup': setup,
        'accept': accept,
        'reject': reject,
        'select': select,
        'retire_setup': retire_setup,
        'retire_play': retire_play,
    }


def build_probe_units(d, scenario, destination_club_id=None):
    mids = verify_stock_chain(d)
    player_field = unique_index(d.fields, BB, 'g_player', 'field')
    myclub_field = unique_index(d.fields, PLAYER, 'm_myclub', 'field')

    if scenario in ('accept', 'reject'):
        # v0 = player.m_myclub; v1/v2 = false; offer = stock m_GetOffer(current club,...)
        units = [
            0x0062, player_field,
            0x0054, myclub_field,
            0x0112,
            0x0212,
            *invoke_static(mids['get_offer'], [0, 1, 2]),
            0x000c,
            0x0112,
            *invoke_static(mids['setup'], [0, 1]),
        ]
        if scenario == 'accept':
            units += [0x0012, *invoke_static(mids['accept'], [0])]
        else:
            units += invoke_static(mids['reject'], [])
        return units + [0x000e]

    if scenario == 'transfer':
        if destination_club_id is None or not (0 <= destination_club_id <= 0x7fff):
            raise ValueError('transfer requires --destination-club-id in 0..32767')
        # Select a real club object through stock c_TClub.m_SelectById, create a
        # real stock offer, then let stock p_SignContract perform the transfer.
        return [
            0x0013, destination_club_id,
            0x0112,
            *invoke_static(mids['select'], [0, 1]),
            0x000c,
            0x0112,
            0x0212,
            *invoke_static(mids['get_offer'], [0, 1, 2]),
            0x000c,
            *invoke_virtual(mids['sign'], [0]),
            0x000e,
        ]

    if scenario == 'retire':
        # SetUpScreen computes the real retirement score; ButtonPlay is the
        # authoritative stock writer for m_retired + quick-save.
        return [
            *invoke_static(mids['retire_setup'], []),
            *invoke_static(mids['retire_play'], []),
            0x000e,
        ]

    raise ValueError(f'unknown scenario {scenario!r}')


def patch_dex(data, dex_name, scenario, destination_club_id=None):
    with tempfile.NamedTemporaryFile(suffix='.dex', delete=False) as f:
        f.write(data)
        tmp = f.name
    try:
        d = Dex(tmp)
        try:
            mid, code = find_target(d)
        except ValueError as e:
            if 'expected one' in str(e) and 'found 0' in str(e):
                return data, False, None
            raise
        regs, ins, outs, tries, size, _ = d.disasm(code)
        if tries:
            raise ValueError(f'{TARGET} has try handlers')
        if regs < 4 or outs < 3:
            raise ValueError(f'{TARGET} lacks registers/outs: regs={regs} outs={outs}')
        units = build_probe_units(d, scenario, destination_club_id)
        if size < len(units):
            raise ValueError(f'{TARGET} too small: {size} < {len(units)}')
        blob = bytearray(data)
        off = code + 16
        struct.pack_into(f'<{size}H', blob, off, *(units + [0] * (size - len(units))))
        blob[12:32] = hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I', blob, 8, zlib.adler32(blob[12:]) & 0xffffffff)
        detail = f' destination_club_id={destination_club_id}' if destination_club_id is not None else ''
        return bytes(blob), True, (
            f'STAGE2 residual TEST-ONLY trigger: {dex_name} {TARGET} method@{mid} '
            f'-> scenario={scenario}{detail}; durable mutations remain inside stock '
            f'm_GetOffer/m_ButtonAccept/m_ButtonReject/p_SignContract/m_SelectById/'
            f'c_TScreen_Retirement.m_ButtonPlay writers'
        )
    finally:
        Path(tmp).unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input_apk', type=Path)
    ap.add_argument('output_apk', type=Path)
    ap.add_argument('--scenario', required=True, choices=('accept', 'reject', 'transfer', 'retire'))
    ap.add_argument('--destination-club-id', type=int)
    args = ap.parse_args()

    entries = []
    patched = 0
    evidence = []
    with zipfile.ZipFile(args.input_apk) as zin:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex', Path(info.filename).name):
                data, changed, ev = patch_dex(data, Path(info.filename).name, args.scenario, args.destination_club_id)
                if changed:
                    patched += 1
                    evidence.append(ev)
            entries.append((info, data))
    if patched != 1:
        raise SystemExit(f'expected exactly one patched DEX, found {patched}')

    with zipfile.ZipFile(args.output_apk, 'w') as zout:
        for info, data in entries:
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = info.compress_type
            zi.comment = info.comment
            zi.extra = info.extra
            zi.internal_attr = info.internal_attr
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zi.flag_bits = info.flag_bits
            zout.writestr(zi, data)
    print('\n'.join(evidence))
    print(f'Wrote TEST-ONLY Stage2 residual probe APK: {args.output_apk}')


if __name__ == '__main__':
    main()
