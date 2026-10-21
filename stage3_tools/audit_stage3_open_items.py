#!/usr/bin/env python3
from __future__ import annotations

import re
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dex_inspect import Dex

SCREEN_MATCH = 'Lcom/newstargames/newstarsoccer/c_TScreen_Match;'
MATCH = 'Lcom/newstargames/newstarsoccer/c_TMatch;'
PLAYER = 'Lcom/newstargames/newstarsoccer/c_TPlayer;'
FIXTURE = 'Lcom/newstargames/newstarsoccer/c_TFixture;'
TARGET_CLASSES = (SCREEN_MATCH, MATCH, PLAYER, FIXTURE)
SIDE_RE = re.compile(r'injur|card|fitness|energy|skill|fatigue|tired|rating|stat', re.I)


def proto_signature(d: Dex, method_id: int):
    _owner, _name, proto_id = d.methods[method_id]
    shorty_idx, return_type_idx, params_off = struct.unpack_from('<III', d.b, d.proto_off + 12 * proto_id)
    params = []
    if params_off:
        count = struct.unpack_from('<I', d.b, params_off)[0]
        params = [d.types[struct.unpack_from('<H', d.b, params_off + 4 + 2 * i)[0]] for i in range(count)]
    return d.types[return_type_idx], params, d.strings[shorty_idx]


def inspect_dex(path: Path, label: str):
    d = Dex(path)
    found_sim = []
    lines = []

    for kind, mid, method, access, code in d.class_methods(SCREEN_MATCH) or []:
        if method[1] != 'm_SimulateMatch':
            continue
        ret, params, shorty = proto_signature(d, mid)
        found_sim.append((mid, access, code, ret, params, shorty))
        lines.append(f'SIMULATE dex={label} kind={kind} method_id={mid} access=0x{access:x} code=0x{code:x} proto={params}->{ret} shorty={shorty}')
        if code:
            regs, ins, outs, tries, size, items = d.disasm(code)
            lines.append(f'SIMULATE_CODE regs={regs} ins={ins} outs={outs} tries={tries} units={size}')
            for off, op, args, raw in items:
                if args or op.startswith(('invoke-', 'sput', 'iput', 'aput', 'sget', 'iget')):
                    lines.append(f'  {off:05x} {op:<24} {args}')

    for cls in TARGET_CLASSES:
        methods = d.class_methods(cls) or []
        named = sorted({m[2][1] for m in methods if SIDE_RE.search(m[2][1])})
        if named:
            lines.append(f'SIDE_METHOD_NAMES dex={label} class={cls} names={named}')
        for kind, mid, method, access, code in methods:
            if not code:
                continue
            _regs, _ins, _outs, _tries, _size, items = d.disasm(code)
            refs = []
            for off, op, args, _raw in items:
                if args and SIDE_RE.search(args):
                    refs.append(f'{off:05x}:{op}:{args}')
            if refs:
                lines.append(f'SIDE_REFS dex={label} caller={cls}->{method[1]} method_id={mid}')
                lines.extend(f'  {r}' for r in refs[:80])

    return found_sim, lines


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit_stage3_open_items.py BASE_APK')
    apk = Path(sys.argv[1])
    sim_hits = []
    all_lines = []
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for name in z.namelist():
            if not re.fullmatch(r'classes\d*\.dex', Path(name).name):
                continue
            out = Path(td) / Path(name).name
            out.write_bytes(z.read(name))
            hits, lines = inspect_dex(out, Path(name).name)
            sim_hits.extend((Path(name).name, *h) for h in hits)
            all_lines.extend(lines)

    if len(sim_hits) != 1:
        raise SystemExit(f'expected exactly one c_TScreen_Match.m_SimulateMatch, found {sim_hits}')

    print('STAGE3_OPEN_ITEMS_STATIC_AUDIT')
    print('\n'.join(all_lines))
    print(f'SIMULATE_HIT_COUNT={len(sim_hits)}')
    print('VERDICT=STAGE3_OPEN_ITEMS_STATIC_AUDIT_PASS')


if __name__ == '__main__':
    main()
