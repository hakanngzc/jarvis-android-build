#!/usr/bin/env python3
from __future__ import annotations

import csv
import io
import zipfile

TABLES = {
    'clubs': ('assets/monkey/MyData/v2025/Clubs.txt', 'shortname'),
    'nations': ('assets/monkey/MyData/v2025/Nations.txt', 'name'),
    'competitions': ('assets/monkey/MyData/v2025/Competitions.txt', 'name'),
}
CLUB_REF_COLUMNS = ('nationid', 'leagueid', 'continentalcompid', 'bteamof')


def _is_meta(row: dict[str, str]) -> bool:
    raw = str(row.get('id') or '').strip()
    return not raw or raw.startswith(('//', '#', ';'))


def _read_table(data: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = data.decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text), delimiter='\t')
    fields = list(reader.fieldnames or [])
    rows = list(reader)
    if 'id' not in fields:
        raise ValueError('missing id column')
    return fields, rows


def _identity(rows: list[dict[str, str]], refs: tuple[str, ...] = ()) -> dict:
    ids = []
    meta = []
    persistent = {}
    for pos, row in enumerate(rows):
        if _is_meta(row):
            meta.append((pos, str(row.get('id') or '')))
            continue
        rid = int(str(row['id']).strip())
        ids.append(rid)
        persistent[rid] = tuple(str(row.get(col) or '') for col in refs)
    return {'ids': ids, 'meta': meta, 'refs': persistent}


def _write_table(fields: list[str], rows: list[dict[str, str]]) -> bytes:
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=fields, delimiter='\t', lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode('utf-8')


def patch_apk_bytes(apk_bytes: bytes, suffix: str = '~') -> tuple[bytes, dict]:
    if any(ch in suffix for ch in '\t\r\n'):
        raise ValueError('control separator in suffix')
    if not suffix:
        raise ValueError('suffix must not be empty')

    src = io.BytesIO(apk_bytes)
    dst = io.BytesIO()
    changed = {group: 0 for group in TABLES}
    identity_preserved = True
    refs_preserved = True
    seen = set()

    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, 'w') as zout:
        path_to_group = {path: group for group, (path, _field) in TABLES.items()}
        for info in zin.infolist():
            data = zin.read(info.filename)
            group = path_to_group.get(info.filename)
            if group is not None:
                path, name_field = TABLES[group]
                fields, rows = _read_table(data)
                if name_field not in fields:
                    raise ValueError(f'{group}: missing name field {name_field}')
                refs = CLUB_REF_COLUMNS if group == 'clubs' else ()
                before = _identity(rows, refs)
                for row in rows:
                    if _is_meta(row):
                        continue
                    old = str(row.get(name_field) or '')
                    row[name_field] = old + suffix
                    changed[group] += 1
                after = _identity(rows, refs)
                identity_preserved = identity_preserved and before['ids'] == after['ids'] and before['meta'] == after['meta']
                refs_preserved = refs_preserved and before['refs'] == after['refs']
                if not identity_preserved:
                    raise ValueError(f'{group}: identity/order contract changed')
                if not refs_preserved:
                    raise ValueError(f'{group}: persistent references changed')
                data = _write_table(fields, rows)
                seen.add(path)

            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = info.compress_type
            zi.comment = info.comment
            zi.extra = info.extra
            zi.internal_attr = info.internal_attr
            zi.external_attr = info.external_attr
            zi.create_system = info.create_system
            zi.flag_bits = info.flag_bits
            zout.writestr(zi, data)

    missing = [path for path, _field in TABLES.values() if path not in seen]
    if missing:
        raise ValueError(f'missing football tables: {missing}')

    report = {
        'changed': changed,
        'changed_total': sum(changed.values()),
        'identity_contract_preserved': identity_preserved,
        'persistent_references_preserved': refs_preserved,
        'suffix': suffix,
    }
    return dst.getvalue(), report
