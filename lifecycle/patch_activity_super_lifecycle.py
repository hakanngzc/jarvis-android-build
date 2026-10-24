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
ACTIVITY = 'Landroid/app/Activity;'
TARGET_METHOD = 'onStop'


def rewrite_super_call(units: list[int], *, resume_method_id: int, target_method_id: int) -> list[int]:
    if not 0 <= resume_method_id <= 0xFFFF:
        raise ValueError(f'resume_method_id does not fit a 16-bit DEX index: {resume_method_id}')
    if not 0 <= target_method_id <= 0xFFFF:
        raise ValueError(f'target_method_id does not fit a 16-bit DEX index: {target_method_id}')
    if len(units) < 3 or units[0] != 0x106F or units[1] != resume_method_id or units[2] != 0x0002:
        raise ValueError('method no longer starts with verified invoke-super Activity.onResume {p0}')
    out = list(units)
    out[1] = target_method_id
    return out


def _unique_method_ref(d: Dex, owner: str, name: str) -> int:
    hits = [i for i, item in enumerate(d.methods) if item[0] == owner and item[1] == name]
    if len(hits) != 1:
        raise ValueError(f'expected exactly one method ref {owner}->{name}, found {hits}')
    return hits[0]


def patch_dex(data: bytes, dex_name: str) -> tuple[bytes, bool, dict | None]:
    with tempfile.NamedTemporaryFile(suffix='.dex', delete=False) as f:
        f.write(data)
        temp_name = f.name
    try:
        d = Dex(temp_name)
        hits = [m for m in (d.class_methods(ANDROID_GAME) or []) if m[2][1] == TARGET_METHOD and m[4]]
        if not hits:
            return data, False, None
        if len(hits) != 1:
            raise ValueError(f'expected one coded {ANDROID_GAME}->{TARGET_METHOD}, found {len(hits)}')

        _kind, method_id, _method_tuple, access, code = hits[0]
        registers, ins, outs, tries, insns_size, _ = d.disasm(code)
        if tries:
            raise ValueError('AndroidGame.onStop has try handlers; refusing unsafe patch')
        if insns_size != 28:
            raise ValueError(f'AndroidGame.onStop size changed; expected 28 units, found {insns_size}')

        resume_id = _unique_method_ref(d, ACTIVITY, 'onResume')
        stop_id = _unique_method_ref(d, ACTIVITY, 'onStop')

        blob = bytearray(data)
        insns_off = code + 16
        current = list(struct.unpack_from('<28H', blob, insns_off))
        replacement = rewrite_super_call(current, resume_method_id=resume_id, target_method_id=stop_id)
        diffs = [i for i, (a, b) in enumerate(zip(current, replacement)) if a != b]
        if diffs != [1]:
            raise ValueError(f'unexpected AndroidGame.onStop diff positions: {diffs}')
        struct.pack_into('<28H', blob, insns_off, *replacement)

        blob[12:32] = hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I', blob, 8, zlib.adler32(blob[12:]) & 0xFFFFFFFF)

        evidence = {
            'dex': dex_name,
            'class': ANDROID_GAME,
            'method': TARGET_METHOD,
            'method_id': method_id,
            'access': access,
            'code_offset': code,
            'registers': registers,
            'ins': ins,
            'outs': outs,
            'tries': tries,
            'insns_size': insns_size,
            'before_insns_sha256': hashlib.sha256(struct.pack('<28H', *current)).hexdigest(),
            'after_insns_sha256': hashlib.sha256(struct.pack('<28H', *replacement)).hexdigest(),
            'changed_code_unit_indices': diffs,
            'activity_onresume_method_ref': resume_id,
            'activity_onstop_method_ref': stop_id,
            'before': 'invoke-super Activity.onResume',
            'after': 'invoke-super Activity.onStop',
            'onstart_unchanged': True,
            'onrestart_unchanged': True,
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
    ap = argparse.ArgumentParser(description='NSS 4.31 candidate Activity onStop super-call fix')
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
        'verdict': 'LIFECYCLE_ACTIVITY_ONSTOP_PATCH_APPLIED',
    }, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print('ANDROIDGAME_ONSTOP_SUPER=Activity.onStop')
    print('ANDROIDGAME_ONSTART_UNCHANGED=true')
    print('ANDROIDGAME_ONRESTART_UNCHANGED=true')
    print('VERDICT=LIFECYCLE_ACTIVITY_ONSTOP_PATCH_APPLIED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
