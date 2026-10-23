#!/usr/bin/env python3
import re
import struct
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'stage1_public'))
from dex_inspect import Dex

TARGET_CLASSES = {
    'Lcom/newstargames/newstarsoccer/c_TClub;',
    'Lcom/newstargames/newstarsoccer/c_TBase_Team;',
}
FIELD_TERMS = ('style', 'kit', 'col', 'colour', 'color', 'badge', 'shield')
UI_STRINGS = {
    'BadgeStyle1', 'BadgeStyle2',
    'Badge1Col1', 'Badge1Col2', 'Badge2Col1', 'Badge2Col2',
    'MatchColours',
}


def iter_methods(d):
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
        for kind, count in [('direct', dm), ('virtual', vm)]:
            mid = 0
            for _ in range(count):
                diff, o = d.uleb(o)
                mid += diff
                access, o = d.uleb(o)
                code, o = d.uleb(o)
                yield desc, kind, mid, d.methods[mid], access, code


def interesting_window(items, hit_indexes, radius=4):
    keep = set()
    for idx in hit_indexes:
        lo = max(0, idx - radius)
        hi = min(len(items), idx + radius + 1)
        keep.update(range(lo, hi))
    return [(idx, items[idx]) for idx in sorted(keep)]


def main():
    if len(sys.argv) != 3:
        raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.txt')
    apk = Path(sys.argv[1])
    out = Path(sys.argv[2])
    lines = []
    total_field_hits = 0
    total_ui_hits = 0
    target_field_names = set()

    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        dex_names = sorted(n for n in z.namelist() if n.startswith('classes') and n.endswith('.dex'))
        for dex_name in dex_names:
            path = Path(td) / Path(dex_name).name
            path.write_bytes(z.read(dex_name))
            d = Dex(path)

            target_fields = []
            candidate_field_ids = set()
            for idx, (cls, name, typ) in enumerate(d.fields):
                if cls in TARGET_CLASSES:
                    target_fields.append((idx, cls, name, typ))
                    if any(term in name.lower() for term in FIELD_TERMS):
                        candidate_field_ids.add(idx)
                        target_field_names.add(name)

            present_ui_strings = sorted(s for s in UI_STRINGS if s in d.strings)
            if not target_fields and not present_ui_strings:
                continue

            lines.append(f'===== {dex_name} =====')
            if target_fields:
                lines.append('TARGET_FIELDS')
                for idx, cls, name, typ in target_fields:
                    mark = ' *BADGE-CANDIDATE*' if idx in candidate_field_ids else ''
                    lines.append(f'field@{idx} {cls}->{name}:{typ}{mark}')
            lines.append('PRESENT_UI_STRINGS=' + ';'.join(present_ui_strings))

            field_tokens = {f'[field@{idx}]' for idx in candidate_field_ids}
            ui_repr = {repr(s): s for s in present_ui_strings}

            for desc, kind, mid, method, access, code in iter_methods(d):
                if not code:
                    continue
                try:
                    _, _, _, _, _, items = d.disasm(code, limit=30000)
                except Exception:
                    continue
                hit_indexes = []
                hit_field = False
                hit_ui = set()
                for n, (_, opname, args, _) in enumerate(items):
                    if any(tok in args for tok in field_tokens):
                        hit_indexes.append(n)
                        hit_field = True
                    if opname in ('const-string', 'const-string/jumbo') and args in ui_repr:
                        hit_indexes.append(n)
                        hit_ui.add(ui_repr[args])
                if not hit_indexes:
                    continue
                if hit_field:
                    total_field_hits += 1
                total_ui_hits += len(hit_ui)
                lines.append('')
                lines.append(
                    f'METHOD class={desc} kind={kind} id={mid} name={method[1]} '
                    f'access={access:#x} code={code:#x} '
                    f'field_hit={int(hit_field)} ui_strings={";".join(sorted(hit_ui))}'
                )
                for idx, item in interesting_window(items, hit_indexes):
                    off, opname, args, raw = item
                    lines.append(f'{idx:05d} {off:05x}: {raw:<28} {opname:<25} {args}')

    if not target_field_names:
        raise SystemExit('no badge/style/kit/colour candidate fields found on c_TClub/c_TBase_Team')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('BADGE_DATA_FLOW_DUMP=PASS')
    print('candidate_fields=' + ','.join(sorted(target_field_names)))
    print(f'methods_with_candidate_field_refs={total_field_hits}')
    print(f'ui_string_method_hits={total_ui_hits}')
    print(f'out={out}')


if __name__ == '__main__':
    main()
