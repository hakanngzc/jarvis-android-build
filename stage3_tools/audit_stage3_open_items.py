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
SPECIAL_CLASS_RE = re.compile(r'Dilemma|SplashMessage', re.I)
SIM_STRING_RE = re.compile(r'Simulate(?:Negative|Neutral|Positive)', re.I)


def proto_signature(d: Dex, method_id: int):
    _owner, _name, proto_id = d.methods[method_id]
    shorty_idx, return_type_idx, params_off = struct.unpack_from('<III', d.b, d.proto_off + 12 * proto_id)
    params = []
    if params_off:
        count = struct.unpack_from('<I', d.b, params_off)[0]
        params = [d.types[struct.unpack_from('<H', d.b, params_off + 4 + 2 * i)[0]] for i in range(count)]
    return d.types[return_type_idx], params, d.strings[shorty_idx]


def all_defined_methods(d: Dex):
    b = d.b
    for j in range(d.class_n):
        vals = struct.unpack_from('<8I', b, d.class_off + 32 * j)
        class_idx, data_off = vals[0], vals[6]
        if not data_off:
            continue
        desc = d.types[class_idx]
        o = data_off
        sf, o = d.uleb(o)
        inf, o = d.uleb(o)
        dm, o = d.uleb(o)
        vm, o = d.uleb(o)
        for _ in range(sf + inf):
            _, o = d.uleb(o)
            _, o = d.uleb(o)
        for kind, count in (('direct', dm), ('virtual', vm)):
            mid = 0
            for _ in range(count):
                diff, o = d.uleb(o)
                mid += diff
                access, o = d.uleb(o)
                code, o = d.uleb(o)
                yield desc, kind, mid, d.methods[mid], access, code


def trace_method_callers(d: Dex, target_ids: set[int], label: str, lines: list[str]):
    needles = {mid: f'[method@{mid}]' for mid in target_ids}
    counts = {mid: 0 for mid in target_ids}
    for desc, kind, mid, method, access, code in all_defined_methods(d):
        if not code:
            continue
        _regs, _ins, _outs, _tries, _size, items = d.disasm(code)
        for target_mid, needle in needles.items():
            hit_indexes = [i for i, item in enumerate(items) if needle in item[2]]
            if not hit_indexes:
                continue
            counts[target_mid] += 1
            lines.append(f'{label}_CALLER target={target_mid} caller={desc}->{method[1]} method_id={mid}')
            for hit_index in hit_indexes:
                start = max(0, hit_index - 18)
                end = min(len(items), hit_index + 10)
                for off, op, args, raw in items[start:end]:
                    lines.append(f'  {off:05x} {raw:<28} {op:<24} {args}')
    for mid, count in sorted(counts.items()):
        lines.append(f'{label}_CALLER_COUNT target={mid} count={count}')


def inspect_dex(path: Path, label: str):
    d = Dex(path)
    found_sim = []
    lines = []
    simulate_mid = None
    simulate_helpers: set[int] = set()

    for kind, mid, method, access, code in d.class_methods(SCREEN_MATCH) or []:
        if method[1] == 'm_SimulateMatch':
            ret, params, shorty = proto_signature(d, mid)
            found_sim.append((mid, access, code, ret, params, shorty))
            simulate_mid = mid
            lines.append(f'SIMULATE dex={label} kind={kind} method_id={mid} access=0x{access:x} code=0x{code:x} proto={params}->{ret} shorty={shorty}')
            if code:
                regs, ins, outs, tries, size, items = d.disasm(code)
                lines.append(f'SIMULATE_CODE regs={regs} ins={ins} outs={outs} tries={tries} units={size}')
                for off, op, args, raw in items:
                    if args or op.startswith(('invoke-', 'sput', 'iput', 'aput', 'sget', 'iget')):
                        lines.append(f'  {off:05x} {raw:<28} {op:<24} {args}')
        elif method[1] in {'m_SimulateNegative', 'm_SimulateNeutral', 'm_SimulatePositive'}:
            simulate_helpers.add(mid)
            lines.append(f'SIMULATE_HELPER dex={label} name={method[1]} method_id={mid} code=0x{code:x}')

    if simulate_mid is not None:
        trace_method_callers(d, {simulate_mid}, 'SIMULATE', lines)
    if simulate_helpers:
        trace_method_callers(d, simulate_helpers, 'SIM_HELPER', lines)

    # Find string-dispatch references because Monkey/X screen callbacks can invoke
    # named functions without a direct DEX invoke to the helper method.
    for desc, kind, mid, method, access, code in all_defined_methods(d):
        if not code:
            continue
        _regs, _ins, _outs, _tries, _size, items = d.disasm(code)
        hits = [(i, item) for i, item in enumerate(items) if SIM_STRING_RE.search(item[2] or '')]
        for hit_index, item in hits:
            lines.append(f'SIM_STRING_REF caller={desc}->{method[1]} method_id={mid} hit={item[2]}')
            for off, op, args, raw in items[max(0, hit_index-12):min(len(items), hit_index+16)]:
                lines.append(f'  {off:05x} {raw:<28} {op:<24} {args}')

    # Map post-match optional dilemma/splash screens so the runtime harness can
    # choose a real stock button instead of treating them as unknown.
    for desc in sorted({x for x in d.types if SPECIAL_CLASS_RE.search(x)}):
        methods = d.class_methods(desc) or []
        lines.append(f'SPECIAL_SCREEN class={desc} method_count={len(methods)}')
        for kind, mid, method, access, code in methods:
            ret, params, shorty = proto_signature(d, mid)
            lines.append(f'  SPECIAL_METHOD name={method[1]} id={mid} kind={kind} proto={params}->{ret} code=0x{code:x}')
            if code and re.search(r'Button|Hit|Select|SetUp|Call|Play|Boss|Team|Fan', method[1], re.I):
                _regs, _ins, _outs, _tries, _size, items = d.disasm(code)
                for off, op, args, raw in items:
                    if args or op.startswith(('invoke-', 'sput', 'iput', 'aput', 'sget', 'iget')):
                        lines.append(f'    {off:05x} {raw:<28} {op:<24} {args}')

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
