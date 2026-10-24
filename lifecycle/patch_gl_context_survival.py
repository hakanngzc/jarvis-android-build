#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
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

ANDROID_GAME = 'Lcom/newstargames/newstarsoccer/AndroidGame;'
GAME_VIEW = 'Lcom/newstargames/newstarsoccer/AndroidGame$GameView;'
BB_ANDROID_GAME = 'Lcom/newstargames/newstarsoccer/BBAndroidGame;'
FOCUS_METHOD = 'onWindowFocusChanged'


def build_focus_sequences(*, view_field_id: int, view_resume_method_id: int,
                          game_field_id: int, game_resume_method_id: int,
                          game_suspend_method_id: int,
                          view_pause_method_id: int) -> tuple[list[int], list[int]]:
    ids = {
        'view_field_id': view_field_id,
        'view_resume_method_id': view_resume_method_id,
        'game_field_id': game_field_id,
        'game_resume_method_id': game_resume_method_id,
        'game_suspend_method_id': game_suspend_method_id,
        'view_pause_method_id': view_pause_method_id,
    }
    for label, value in ids.items():
        if not 0 <= value <= 0xFFFF:
            raise ValueError(f'{label} does not fit a 16-bit DEX index: {value}')

    stock = [
        0x0138, 0x000D,
        0x0154, view_field_id,
        0x106E, view_resume_method_id, 0x0001,
        0x0154, game_field_id,
        0x106E, game_resume_method_id, 0x0001,
        0x0B28,
        0x0154, game_field_id,
        0x106E, game_suspend_method_id, 0x0001,
        0x0154, view_field_id,
        0x106E, view_pause_method_id, 0x0001,
        0x000E,
    ]
    patched = [
        0x0138, 0x000D,
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        0x0154, game_field_id,
        0x106E, game_resume_method_id, 0x0001,
        0x0B28,
        0x0154, game_field_id,
        0x106E, game_suspend_method_id, 0x0001,
        0x0000, 0x0000, 0x0000, 0x0000, 0x0000,
        0x000E,
    ]
    return stock, patched


def rewrite_focus_units(units: list[int], **ids: int) -> list[int]:
    stock, patched = build_focus_sequences(**ids)
    if units != stock:
        raise ValueError('AndroidGame.onWindowFocusChanged no longer matches verified NSS 4.31 stock body')
    return patched


def _unique_index(items, owner: str, name: str, kind: str) -> int:
    hits = [i for i, item in enumerate(items) if item[0] == owner and item[1] == name]
    if len(hits) != 1:
        raise ValueError(f'expected exactly one {kind} {owner}->{name}, found {hits}')
    return hits[0]


def patch_dex(data: bytes, dex_name: str) -> tuple[bytes, bool, dict | None]:
    with tempfile.NamedTemporaryFile(suffix='.dex', delete=False) as f:
        f.write(data)
        temp_name = f.name
    try:
        d = Dex(temp_name)
        hits = [m for m in (d.class_methods(ANDROID_GAME) or [])
                if m[2][1] == FOCUS_METHOD and m[4]]
        if not hits:
            return data, False, None
        if len(hits) != 1:
            raise ValueError(f'expected one {ANDROID_GAME}->{FOCUS_METHOD}, found {len(hits)}')

        _kind, method_id, _method_tuple, access, code = hits[0]
        registers, ins, outs, tries, insns_size, _ = d.disasm(code)
        if tries:
            raise ValueError('onWindowFocusChanged has try handlers; refusing unsafe patch')
        if insns_size != 24:
            raise ValueError(f'onWindowFocusChanged size changed; expected 24 units, found {insns_size}')

        ids = dict(
            view_field_id=_unique_index(d.fields, ANDROID_GAME, '_view', 'field'),
            view_resume_method_id=_unique_index(d.methods, GAME_VIEW, 'onResume', 'method'),
            game_field_id=_unique_index(d.fields, ANDROID_GAME, '_game', 'field'),
            game_resume_method_id=_unique_index(d.methods, BB_ANDROID_GAME, 'ResumeGame', 'method'),
            game_suspend_method_id=_unique_index(d.methods, BB_ANDROID_GAME, 'SuspendGame', 'method'),
            view_pause_method_id=_unique_index(d.methods, GAME_VIEW, 'onPause', 'method'),
        )

        blob = bytearray(data)
        insns_off = code + 16
        current = list(struct.unpack_from('<24H', blob, insns_off))
        replacement = rewrite_focus_units(current, **ids)
        struct.pack_into('<24H', blob, insns_off, *replacement)

        before_sha = hashlib.sha256(struct.pack('<24H', *current)).hexdigest()
        after_sha = hashlib.sha256(struct.pack('<24H', *replacement)).hexdigest()
        diffs = [i for i, (a, b) in enumerate(zip(current, replacement)) if a != b]
        expected_diffs = [2, 3, 4, 5, 6, 18, 19, 20, 21, 22]
        if diffs != expected_diffs:
            raise ValueError(f'unexpected focus patch diff positions: {diffs}')

        blob[12:32] = hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I', blob, 8, zlib.adler32(blob[12:]) & 0xFFFFFFFF)

        evidence = {
            'dex': dex_name,
            'class': ANDROID_GAME,
            'method': FOCUS_METHOD,
            'method_id': method_id,
            'access': access,
            'code_offset': code,
            'registers': registers,
            'ins': ins,
            'outs': outs,
            'tries': tries,
            'insns_size': insns_size,
            'before_insns_sha256': before_sha,
            'after_insns_sha256': after_sha,
            'changed_code_unit_indices': diffs,
            'game_suspend_resume_unchanged': True,
            'control_flow_offsets_unchanged': True,
            'glsurfaceview_pause_resume_removed': True,
            'candidate_fix': True,
        }
        return bytes(blob), True, evidence
    finally:
        Path(temp_name).unlink(missing_ok=True)


def patch_apk_bytes(apk_bytes: bytes) -> tuple[bytes, dict]:
    patched = 0
    evidence = None
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(apk_bytes), 'r') as zin, zipfile.ZipFile(out, 'w') as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex', Path(info.filename).name):
                data, changed, row = patch_dex(data, Path(info.filename).name)
                if changed:
                    patched += 1
                    evidence = row
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = info.compress_type
            zi.comment = info.comment
            zi.extra = info.extra
            zi.internal_attr = info.internal_attr
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zi.flag_bits = info.flag_bits
            zout.writestr(zi, data)
    if patched != 1 or evidence is None:
        raise ValueError(f'expected exactly one patched DEX, found {patched}')
    return out.getvalue(), evidence


def main() -> int:
    ap = argparse.ArgumentParser(description='Candidate NSS 4.31 GL context-survival focus patch')
    ap.add_argument('input_apk', type=Path)
    ap.add_argument('output_apk', type=Path)
    ap.add_argument('--evidence', type=Path, required=True)
    args = ap.parse_args()

    patched, evidence = patch_apk_bytes(args.input_apk.read_bytes())
    args.output_apk.parent.mkdir(parents=True, exist_ok=True)
    args.output_apk.write_bytes(patched)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps({
        'schema': 1,
        'input_apk': str(args.input_apk),
        'output_apk': str(args.output_apk),
        'patch': evidence,
        'verdict': 'LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH_APPLIED',
    }, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('GAME_SUSPEND_RESUME_UNCHANGED=true')
    print('GLSURFACEVIEW_PAUSE_RESUME_REMOVED=true')
    print('VERDICT=LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH_APPLIED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
