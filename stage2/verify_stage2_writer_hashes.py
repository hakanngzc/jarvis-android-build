#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dex_inspect import Dex

APP = 'Lcom/newstargames/newstarsoccer/'
TARGETS = [
    (APP+'c_TContractOffer;', 'p_SignContract'),
    (APP+'c_TScreen_Contract;', 'm_ButtonAccept'),
    (APP+'c_TScreen_Contract;', 'm_ButtonReject'),
    (APP+'c_TScreen_Retirement;', 'm_ButtonPlay'),
    (APP+'c_TPlayer;', 'p_QuickSave'),
]


def method_hashes(apk: Path) -> dict:
    out = {}
    with tempfile.TemporaryDirectory(prefix='nss-stage2-writer-hash-') as td:
        td = Path(td)
        dexes = []
        with zipfile.ZipFile(apk) as z:
            for name in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)):
                p = td / name
                p.write_bytes(z.read(name))
                dexes.append((name, Dex(p)))
        for owner, name in TARGETS:
            hits = []
            for dex_name, d in dexes:
                for kind, mid, m, access, code in d.class_methods(owner) or []:
                    if m[1] == name and code:
                        hits.append((dex_name, d, mid, code))
            if len(hits) != 1:
                raise ValueError(f'expected exactly one {owner}->{name}, found {len(hits)}')
            dex_name, d, mid, code = hits[0]
            regs, ins, outs, tries, units, items = d.disasm(code)
            raw = d.b[code + 16: code + 16 + units * 2]
            key = owner + '->' + name
            out[key] = {
                'dex': dex_name,
                'method_index': mid,
                'instruction_units': units,
                'instruction_sha256': hashlib.sha256(raw).hexdigest(),
            }
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('stock_apk', type=Path)
    ap.add_argument('test_apk', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    stock = method_hashes(args.stock_apk)
    test = method_hashes(args.test_apk)
    rows = []
    ok = True
    for key in stock:
        same = stock[key]['instruction_sha256'] == test[key]['instruction_sha256']
        ok = ok and same
        rows.append({'method': key, 'same': same, 'stock': stock[key], 'test': test[key]})
        print(('PASS' if same else 'FAIL'), key, stock[key]['instruction_sha256'])
    result = {'schema': 1, 'all_stock_writers_unchanged': ok, 'methods': rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print('VERDICT=' + ('STAGE2_WRITER_HASH_PASS' if ok else 'STAGE2_WRITER_HASH_FAIL'))
    if not ok:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
