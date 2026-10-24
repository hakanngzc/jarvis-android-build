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
TARGET_SUPERS = {
    'onRestart': 'onRestart',
    'onStart': 'onStart',
    'onStop': 'onStop',
}


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


def patch_dex(data: bytes, dex_name: str) -> tuple[bytes, bool, list[dict] | None]:
    with tempfile.NamedTemporaryFile(suffix='.dex', delete=False) as f:
        f.write(data)
        temp_name = f.name
    try:
        d = Dex(temp_name)
        class_methods = d.class_methods(ANDROID_GAME) or []
        coded_by_name: dict[str, list] = {}
        for m in class_methods:
            if m[4]:
                coded_by_name.setdefault(m[2][1], []).append(m)

        present = [name for name in TARGET_SUPERS if name in coded_by_name]
        if not present:
            return data, False, None
        if set(present) != set(TARGET_SUPERS):
            raise ValueError(f'partial AndroidGame lifecycle target set: found {present}, expected {sorted(TARGET_SUPERS)}')

        resume_id = _unique_method_ref(d, ACTIVITY, 'onResume')
        target_refs = {name: _unique_method_ref(d, ACTIVITY, super_name) for name, super_name in TARGET_SUPERS.items()}
        blob = bytearray(data)
        evidence_rows: list[dict] = []

        for method_name, super_name in TARGET_SUPERS.items():
            hits = coded_by_name.get(method_name, [])
            if len(hits) != 1:
                raise ValueError(f'expected one coded {ANDROID_GAME}->{method_name}, found {len(hits)}')
            _kind, method_id, _method_tuple, access, code = hits[0]
            registers, ins, outs, tries, insns_size, _ = d.disasm(code)
            if tries:
                raise ValueError(f'AndroidGame.{method_name} has try handlers; refusing unsafe patch')
            if insns_size != 28:
                raise ValueError(f'AndroidGame.{method_name} size changed; expected 28 units, found {insns_size}')

            insns_off = code + 16
            current = list(struct.unpack_from('<28H', blob, insns_off))
            replacement = rewrite_super_call(
                current,
                resume_method_id=resume_id,
                target_method_id=target_refs[method_name],
            )
            diffs = [i for i, (a, b) in enumerate(zip(current, replacement)) if a != b]
            if diffs != [1]:
                raise ValueError(f'unexpected AndroidGame.{method_name} diff positions: {diffs}')
            struct.pack_into('<28H', blob, insns_off, *replacement)

            evidence_rows.append({
                'dex': dex_name,
                'class': ANDROID_GAME,
                'method': method_name,
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
                'target_activity_method_ref': target_refs[method_name],
                'before': 'invoke-super Activity.onResume',
                'after': f'invoke-super Activity.{super_name}',
                'candidate_fix': True,
            })

        blob[12:32] = hashlib.sha1(blob[32:]).digest()
        struct.pack_into('<I', blob, 8, zlib.adler32(blob[12:]) & 0xFFFFFFFF)
        return bytes(blob), True, evidence_rows
    finally:
        Path(temp_name).unlink(missing_ok=True)


def patch_apk_bytes(apk_bytes: bytes) -> tuple[bytes, list[dict]]:
    patched_dexes = 0
    evidence: list[dict] | None = None
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(apk_bytes), 'r') as zin, zipfile.ZipFile(out, 'w') as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex', Path(info.filename).name):
                data, changed, rows = patch_dex(data, Path(info.filename).name)
                if changed:
                    patched_dexes += 1
                    evidence = rows
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = info.compress_type
            zi.comment = info.comment
            zi.extra = info.extra
            zi.internal_attr = info.internal_attr
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zi.flag_bits = info.flag_bits
            zout.writestr(zi, data)
    if patched_dexes != 1 or evidence is None:
        raise ValueError(f'expected exactly one patched DEX, found {patched_dexes}')
    if len(evidence) != len(TARGET_SUPERS):
        raise ValueError(f'expected {len(TARGET_SUPERS)} lifecycle patches, found {len(evidence)}')
    return out.getvalue(), evidence


def main() -> int:
    ap = argparse.ArgumentParser(description='NSS 4.31 candidate Activity lifecycle super-call fix')
    ap.add_argument('input_apk', type=Path)
    ap.add_argument('output_apk', type=Path)
    ap.add_argument('--evidence', type=Path, required=True)
    args = ap.parse_args()

    patched, evidence = patch_apk_bytes(args.input_apk.read_bytes())
    args.output_apk.parent.mkdir(parents=True, exist_ok=True)
    args.output_apk.write_bytes(patched)
    args.evidence.parent.mkdir(parents=True, exist_ok=True)
    args.evidence.write_text(json.dumps({
        'schema': 2,
        'input_apk': str(args.input_apk),
        'output_apk': str(args.output_apk),
        'patches': evidence,
        'verdict': 'LIFECYCLE_ACTIVITY_SUPER_PATCH_APPLIED',
    }, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    for row in evidence:
        print(f"ANDROIDGAME_{row['method'].upper()}_SUPER={row['after'].split('Activity.', 1)[1]}")
    print('ANDROIDGAME_ONPAUSE_UNCHANGED=true')
    print('ANDROIDGAME_ONRESUME_UNCHANGED=true')
    print('VERDICT=LIFECYCLE_ACTIVITY_SUPER_PATCH_APPLIED')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
