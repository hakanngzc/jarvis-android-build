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

NSS_PREFIX = 'Lcom/newstargames/newstarsoccer/'
SIDE_RE = re.compile(r'injur|card|susp|ban|fitness|skill|energy|fatigue|tired', re.I)
MATCH_RE = re.compile(r'match|mymatchplayed|endmatch|playtodate|simulate', re.I)
PUT_OPS = {'iput','iput-wide','iput-object','iput-boolean','iput-byte','iput-char','iput-short',
           'sput','sput-wide','sput-object','sput-boolean','sput-byte','sput-char','sput-short'}


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


def audit_dex(path: Path, label: str):
    d = Dex(path)
    lines = []
    candidate_fields = {
        idx: field for idx, field in enumerate(d.fields)
        if field[0].startswith(NSS_PREFIX) and SIDE_RE.search(field[1])
    }
    candidate_methods = {
        idx: method for idx, method in enumerate(d.methods)
        if method[0].startswith(NSS_PREFIX) and SIDE_RE.search(method[1])
    }

    for idx,(owner,name,typ) in sorted(candidate_fields.items()):
        lines.append(f'SIDE_FIELD dex={label} field_id={idx} owner={owner} name={name} type={typ}')
    for idx,(owner,name,_proto) in sorted(candidate_methods.items()):
        ret,params=proto_signature(d,idx)
        lines.append(f'SIDE_METHOD dex={label} method_id={idx} owner={owner} name={name} proto={params}->{ret}')

    field_needles = {idx:f'[field@{idx}]' for idx in candidate_fields}
    method_needles = {idx:f'[method@{idx}]' for idx in candidate_methods}

    for caller_owner,_kind,caller_mid,caller,access,code in all_defined_methods(d):
        if not code or not caller_owner.startswith(NSS_PREFIX):
            continue
        _regs,_ins,_outs,_tries,_size,items=d.disasm(code)
        caller_name=caller[1]
        interesting_caller = bool(MATCH_RE.search(caller_owner) or MATCH_RE.search(caller_name))

        for off,op,args,raw in items:
            if op in PUT_OPS:
                for fid,needle in field_needles.items():
                    if needle in args:
                        owner,name,typ=candidate_fields[fid]
                        lines.append(
                            f'SIDE_WRITE dex={label} caller={caller_owner}->{caller_name} caller_id={caller_mid} '
                            f'offset={off:05x} op={op} target={owner}->{name}:{typ} field_id={fid} '
                            f'match_related={int(interesting_caller)}'
                        )
                        break

            if op.startswith('invoke-'):
                for target_mid,needle in method_needles.items():
                    if needle in args:
                        owner,name,_proto=candidate_methods[target_mid]
                        lines.append(
                            f'SIDE_CALL dex={label} caller={caller_owner}->{caller_name} caller_id={caller_mid} '
                            f'offset={off:05x} target={owner}->{name} method_id={target_mid} '
                            f'match_related={int(interesting_caller)}'
                        )
                        break

    return lines


def main():
    if len(sys.argv)!=2:
        raise SystemExit('usage: audit_stage3_side_effect_writers.py BASE_APK')
    apk=Path(sys.argv[1])
    lines=[]
    with zipfile.ZipFile(apk) as z, tempfile.TemporaryDirectory() as td:
        for name in z.namelist():
            if not re.fullmatch(r'classes\d*\.dex',Path(name).name):
                continue
            out=Path(td)/Path(name).name
            out.write_bytes(z.read(name))
            lines.extend(audit_dex(out,Path(name).name))
    print('STAGE3_SIDE_EFFECT_WRITER_AUDIT')
    print('\n'.join(lines))
    print('VERDICT=STAGE3_SIDE_EFFECT_WRITER_AUDIT_PASS')


if __name__=='__main__':
    main()
