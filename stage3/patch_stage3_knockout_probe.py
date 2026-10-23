#!/usr/bin/env python3
"""TEST-ONLY Stage3 knockout branch probe.

The probe replaces only c_TMatch.m_StartMatch. It seeds the already-selected
fixture as a 0-0 knockout (matchtype=3), places the match at a half boundary,
and then invokes the original c_TMatch.m_DoHalfEnds().

Modes:
- extra-time: m_half=2, so stock DoHalfEnds handles the 90-minute tie.
- shootout:   m_half=4, so stock DoHalfEnds handles the 120-minute tie.

m_DoHalfEnds, m_MatchOver, m_DoShootOut and m_CheckShootOutComplete are never
patched. This harness must never ship in production NSS REBORN builds.
"""
from __future__ import annotations

import hashlib
import io
import re
import struct
import sys
import tempfile
import zlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from dex_inspect import Dex  # noqa: E402

MATCH = 'Lcom/newstargames/newstarsoccer/c_TMatch;'
FIXTURE = 'Lcom/newstargames/newstarsoccer/c_TFixture;'
START_MATCH = 'm_StartMatch'
DO_HALF_ENDS = 'm_DoHalfEnds'
MATCH_OVER = 'm_MatchOver'
DO_SHOOTOUT = 'm_DoShootOut'
CHECK_SHOOTOUT = 'm_CheckShootOutComplete'
VALID_MODES = {'extra-time': 2, 'shootout': 4}


def build_probe_units(*, mode: str, fixture_field_id: int, matchtype_field_id: int,
                      score1_field_id: int, score2_field_id: int, half_field_id: int,
                      do_half_ends_method_id: int) -> list[int]:
    if mode not in VALID_MODES:
        raise ValueError(f'unsupported knockout probe mode: {mode}')
    for label, value in {
        'fixture_field_id': fixture_field_id,
        'matchtype_field_id': matchtype_field_id,
        'score1_field_id': score1_field_id,
        'score2_field_id': score2_field_id,
        'half_field_id': half_field_id,
        'do_half_ends_method_id': do_half_ends_method_id,
    }.items():
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f'{label} does not fit a 16-bit DEX index: {value}')

    half_seed = VALID_MODES[mode]
    half_const = 0x2112 if half_seed == 2 else 0x4112
    return [
        0x0062, fixture_field_id,
        0x3112,
        0x0159, matchtype_field_id,
        0x0112,
        0x0159, score1_field_id,
        0x0159, score2_field_id,
        half_const,
        0x0167, half_field_id,
        0x0071, do_half_ends_method_id, 0x0000,
        0x000E,
    ]


def validate_target_code(*, registers: int, tries: int, insns_size: int, required_units: int) -> None:
    if tries:
        raise ValueError('m_StartMatch has try handlers; refusing unsafe body replacement')
    if registers < 2:
        raise ValueError(f'm_StartMatch needs at least 2 registers, found {registers}')
    if insns_size < required_units:
        raise ValueError(f'm_StartMatch has only {insns_size} code units; need {required_units} code units')


def _unique_index(items, owner: str, name: str, kind: str) -> int:
    hits = [i for i, item in enumerate(items) if item[0] == owner and item[1] == name]
    if len(hits) != 1:
        raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]


def _method_code_info(d: Dex, data: bytes, name: str) -> dict:
    hits = [m for m in (d.class_methods(MATCH) or []) if m[2][1] == name and m[4]]
    if len(hits) != 1:
        raise ValueError(f'expected exactly one coded method {MATCH}->{name}, found {len(hits)}')
    _kind, method_id, _method_tuple, access, code = hits[0]
    registers, ins, outs, tries, insns_size, _ = d.disasm(code)
    insns = data[code + 16: code + 16 + insns_size * 2]
    return {
        'method': name,
        'method_id': method_id,
        'code_offset': code,
        'access': access,
        'registers': registers,
        'ins': ins,
        'outs': outs,
        'tries': tries,
        'insns_size': insns_size,
        'insns_sha256': hashlib.sha256(insns).hexdigest(),
    }


def patch_dex(data: bytes, dex_name: str, mode: str) -> tuple[bytes, bool, dict | None]:
    if mode not in VALID_MODES:
        raise ValueError(f'unsupported knockout probe mode: {mode}')
    with tempfile.NamedTemporaryFile(suffix='.dex', delete=False) as f:
        f.write(data)
        temp_name = f.name
    try:
        d = Dex(temp_name)
        starts = [m for m in (d.class_methods(MATCH) or []) if m[2][1] == START_MATCH and m[4]]
        if not starts:
            return data, False, None
        if len(starts) != 1:
            raise ValueError(f'expected one {MATCH}->{START_MATCH}, found {len(starts)}')
        _kind, method_id, _method_tuple, access, code = starts[0]
        if not (access & 0x8):
            raise ValueError('m_StartMatch is not static; probe encoding would be unsafe')

        fixture_field_id = _unique_index(d.fields, MATCH, 'm_fixture', 'field')
        matchtype_field_id = _unique_index(d.fields, FIXTURE, 'm_matchtype', 'field')
        score1_field_id = _unique_index(d.fields, FIXTURE, 'm_score1', 'field')
        score2_field_id = _unique_index(d.fields, FIXTURE, 'm_score2', 'field')
        half_field_id = _unique_index(d.fields, MATCH, 'm_half', 'field')
        do_half_ends_method_id = _unique_index(d.methods, MATCH, DO_HALF_ENDS, 'method')

        if d.fields[fixture_field_id][2] != FIXTURE:
            raise ValueError('m_fixture type is not c_TFixture')
        for field_id, label in ((matchtype_field_id, 'm_matchtype'), (score1_field_id, 'm_score1'),
                                (score2_field_id, 'm_score2'), (half_field_id, 'm_half')):
            if d.fields[field_id][2] != 'I':
                raise ValueError(f'{label} is not int')

        stock_methods = {name: _method_code_info(d, data, name)
                         for name in (DO_HALF_ENDS, MATCH_OVER, DO_SHOOTOUT, CHECK_SHOOTOUT)}

        registers, ins, outs, tries, insns_size, _ = d.disasm(code)
        units = build_probe_units(mode=mode, fixture_field_id=fixture_field_id,
                                  matchtype_field_id=matchtype_field_id,
                                  score1_field_id=score1_field_id, score2_field_id=score2_field_id,
                                  half_field_id=half_field_id,
                                  do_half_ends_method_id=do_half_ends_method_id)
        validate_target_code(registers=registers, tries=tries, insns_size=insns_size,
                             required_units=len(units))

        blob = bytearray(data)
        insns_off = code + 16
        original_prefix = struct.unpack_from(f'<{len(units)}H', blob, insns_off)
        if list(original_prefix) == units:
            raise ValueError(f'm_StartMatch already contains the Stage3 {mode} probe')
        replacement = units + [0x0000] * (insns_size - len(units))
        struct.pack_into(f'<{insns_size}H', blob, insns_off, *replacement)

        blob[12:32] = hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I', blob, 8, zlib.adler32(blob[12:]) & 0xFFFFFFFF)

        evidence = {
            'dex': dex_name,
            'mode': mode,
            'patched_method': f'{MATCH}->{START_MATCH}',
            'patched_method_id': method_id,
            'patched_code_offset': code,
            'seed_matchtype': 3,
            'seed_score': '0-0',
            'seed_half': VALID_MODES[mode],
            'handoff': f'{MATCH}->{DO_HALF_ENDS}',
            'stock_methods_untouched': stock_methods,
            'test_only_never_ship': True,
        }
        return bytes(blob), True, evidence
    finally:
        Path(temp_name).unlink(missing_ok=True)


def patch_apk_bytes(apk_bytes: bytes, mode: str) -> tuple[bytes, dict]:
    patched = 0
    patch_evidence = None
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(apk_bytes), 'r') as zin, zipfile.ZipFile(out, 'w') as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex', Path(info.filename).name):
                data, changed, evidence = patch_dex(data, Path(info.filename).name, mode)
                if changed:
                    patched += 1
                    patch_evidence = evidence
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = info.compress_type
            zi.comment = info.comment
            zi.extra = info.extra
            zi.internal_attr = info.internal_attr
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zi.flag_bits = info.flag_bits
            zout.writestr(zi, data)
    if patched != 1 or not patch_evidence:
        raise ValueError(f'expected exactly one patched DEX, found {patched}')
    return out.getvalue(), patch_evidence
