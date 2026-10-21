#!/usr/bin/env python3
from __future__ import annotations

import re
import struct
import sys
import tempfile
import zipfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dex_inspect import Dex

NSS = 'Lcom/newstargames/newstarsoccer/'
CATEGORIES = {
    'injury': re.compile(r'injur|injured|injury|hurt', re.I),
    'discipline': re.compile(r'yellow(?:card)?|redcard|red_card|booked|booking|sentoff|sent_off|suspension|playerban|matchban', re.I),
    'fitness': re.compile(r'fitness|stamina|fatigue|tired|energy', re.I),
    'skill': re.compile(r'skill', re.I),
}
MATCH_RE = re.compile(r'match|mymatchplayed|endmatch|playtodate|simulate', re.I)
PUT_PREFIX = ('iput', 'sput')


def proto_signature(d: Dex, method_id: int):
    _owner, _name, proto_id = d.methods[method_id]
    _shorty_idx, return_type_idx, params_off = struct.unpack_from('<III', d.b, d.proto_off + 12 * proto_id)
    params = []
    if params_off:
        count = struct.unpack_from('<I', d.b, params_off)[0]
        params = [d.types[struct.unpack_from('<H', d.b, params_off + 4 + 2*i)[0]] for i in range(count)]
    return d.types[return_type_idx], params


def all_defined_methods(d: Dex):
    b = d.b
    for j in range(d.class_n):
        vals = struct.unpack_from('<8I', b, d.class_off + 32*j)
        class_idx, data_off = vals[0], vals[6]
        if not data_off:
            continue
        desc = d.types[class_idx]
        o = data_off
        sf,o=d.uleb(o); inf,o=d.uleb(o); dm,o=d.uleb(o); vm,o=d.uleb(o)
        for _ in range(sf+inf):
            _,o=d.uleb(o); _,o=d.uleb(o)
        for kind,count in (('direct',dm),('virtual',vm)):
            mid=0
            for _ in range(count):
                diff,o=d.uleb(o); mid+=diff
                access,o=d.uleb(o); code,o=d.uleb(o)
                yield desc,kind,mid,d.methods[mid],access,code


def category_for(text: str):
    return [name for name, rx in CATEGORIES.items() if rx.search(text)]


def is_game_owner(owner: str) -> bool:
    return owner.startswith(NSS) and '/R$' not in owner and not owner.endswith('/R;')


def audit_dex(path: Path, label: str):
    d = Dex(path)
    out = []
    counts = defaultdict(int)

    fields = {}
    for idx, (owner, name, typ) in enumerate(d.fields):
        if not is_game_owner(owner):
            continue
        cats = category_for(name)
        if not cats:
            continue
        # Exclude engine lifecycle suspension; it is app pause/resume, not football discipline.
        if name == '_suspended' and owner.endswith(('BBGame;', 'BBAndroidGame;')):
            continue
        fields[idx] = (owner, name, typ, cats)
        for cat in cats:
            counts[f'{cat}_fields'] += 1
        out.append(f'DOMAIN_FIELD dex={label} field_id={idx} cats={"+".join(cats)} owner={owner} name={name} type={typ}')

    methods = {}
    for idx, (owner, name, _proto) in enumerate(d.methods):
        if not is_game_owner(owner):
            continue
        cats = category_for(name)
        if not cats:
            continue
        if name in {'SuspendGame', 'Suspended'} and owner.endswith('BBGame;'):
            continue
        methods[idx] = (owner, name, cats)
        ret, params = proto_signature(d, idx)
        for cat in cats:
            counts[f'{cat}_methods'] += 1
        out.append(f'DOMAIN_METHOD dex={label} method_id={idx} cats={"+".join(cats)} owner={owner} name={name} proto={params}->{ret}')

    field_needles = {idx: f'[field@{idx}]' for idx in fields}
    method_needles = {idx: f'[method@{idx}]' for idx in methods}

    for caller_owner, _kind, caller_mid, caller, _access, code in all_defined_methods(d):
        if not code or not is_game_owner(caller_owner):
            continue
        _regs, _ins, _outs, _tries, _size, items = d.disasm(code)
        caller_name = caller[1]
        match_related = bool(MATCH_RE.search(caller_owner) or MATCH_RE.search(caller_name))
        for i, (off, op, args, raw) in enumerate(items):
            if op.startswith(PUT_PREFIX):
                for fid, needle in field_needles.items():
                    if needle not in args:
                        continue
                    owner, name, typ, cats = fields[fid]
                    for cat in cats:
                        counts[f'{cat}_writes'] += 1
                        if match_related:
                            counts[f'{cat}_match_writes'] += 1
                    out.append(
                        f'DOMAIN_WRITE dex={label} cats={"+".join(cats)} caller={caller_owner}->{caller_name} '
                        f'caller_id={caller_mid} offset={off:05x} op={op} target={owner}->{name}:{typ} '
                        f'match_related={int(match_related)}'
                    )
                    break
            if op.startswith('invoke-'):
                for target_mid, needle in method_needles.items():
                    if needle not in args:
                        continue
                    owner, name, cats = methods[target_mid]
                    for cat in cats:
                        counts[f'{cat}_calls'] += 1
                        if match_related:
                            counts[f'{cat}_match_calls'] += 1
                    out.append(
                        f'DOMAIN_CALL dex={label} cats={"+".join(cats)} caller={caller_owner}->{caller_name} '
                        f'caller_id={caller_mid} offset={off:05x} target={owner}->{name} method_id={target_mid} '
                        f'match_related={int(match_related)}'
                    )
                    # Print bounded caller context for potentially important match or skill depletion links.
                    if match_related or 'DepleteSkill' in name or 'CheckSkillDeplete' in name:
                        for coff, cop, cargs, craw in items[max(0, i-12):min(len(items), i+12)]:
                            out.append(f'  CTX {coff:05x} {craw:<28} {cop:<24} {cargs}')
                    break

    # Strings are evidence that a domain exists even when field/method names are opaque.
    for idx, text in enumerate(d.strings):
        if len(text) > 160:
            continue
        cats = category_for(text)
        if not cats:
            continue
        if re.fullmatch(r'[A-Za-z0-9_.$/;:-]+', text) and ('android' in text.lower() or 'cardview' in text.lower()):
            continue
        for cat in cats:
            counts[f'{cat}_strings'] += 1
        out.append(f'DOMAIN_STRING dex={label} string_id={idx} cats={"+".join(cats)} text={text!r}')

    return out, counts


def main():
    if len(sys.argv) != 2:
        raise SystemExit('usage: audit_stage3_domain_side_effects.py BASE_APK')
    apk = Path(sys.argv[1])
    lines = []
    total = defaultdict(int)
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for name in z.namelist():
            if not re.fullmatch(r'classes\d*\.dex', Path(name).name):
                continue
            out = Path(td) / Path(name).name
            out.write_bytes(z.read(name))
            dex_lines, counts = audit_dex(out, Path(name).name)
            lines.extend(dex_lines)
            for k, v in counts.items():
                total[k] += v

    print('STAGE3_DOMAIN_SIDE_EFFECT_AUDIT')
    print('\n'.join(lines))
    for cat in CATEGORIES:
        print(
            f'SUMMARY category={cat} fields={total[f"{cat}_fields"]} methods={total[f"{cat}_methods"]} '
            f'writes={total[f"{cat}_writes"]} calls={total[f"{cat}_calls"]} '
            f'match_writes={total[f"{cat}_match_writes"]} match_calls={total[f"{cat}_match_calls"]} '
            f'strings={total[f"{cat}_strings"]}'
        )
    print('VERDICT=STAGE3_DOMAIN_SIDE_EFFECT_AUDIT_PASS')


if __name__ == '__main__':
    main()
