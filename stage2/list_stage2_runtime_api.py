#!/usr/bin/env python3
import argparse, re, struct, tempfile, zipfile
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.dex_inspect import Dex

TARGETS = [
    'Lcom/newstargames/newstarsoccer/c_TContractOffer;',
    'Lcom/newstargames/newstarsoccer/c_TClub;',
    'Lcom/newstargames/newstarsoccer/c_TScreen_Contract;',
    'Lcom/newstargames/newstarsoccer/c_TScreen_Retirement;',
    'Lcom/newstargames/newstarsoccer/c_TPlayer;',
    'Lcom/newstargames/newstarsoccer/c_List29;',
]

def proto_desc(d: Dex, proto_idx: int) -> str:
    off = d.proto_off + 12 * proto_idx
    _, return_idx, params_off = struct.unpack_from('<III', d.b, off)
    args = []
    if params_off:
        size = struct.unpack_from('<I', d.b, params_off)[0]
        for i in range(size):
            ti = struct.unpack_from('<H', d.b, params_off + 4 + 2*i)[0]
            args.append(d.types[ti])
    return '(' + ''.join(args) + ')' + d.types[return_idx]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('base_apk', type=Path); a=ap.parse_args()
    with tempfile.TemporaryDirectory(prefix='nss-stage2-api-') as td:
        td=Path(td); dexes=[]
        with zipfile.ZipFile(a.base_apk) as z:
            for name in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex', n)):
                p=td/name; p.write_bytes(z.read(name)); dexes.append((name,Dex(p)))
        for desc in TARGETS:
            print('\nCLASS', desc)
            for dn,d in dexes:
                ms=d.class_methods(desc)
                if not ms: continue
                print('DEX',dn)
                print('FIELDS')
                for c,n,t in d.fields:
                    if c==desc: print(' ',n,t)
                print('METHODS')
                for kind,mid,m,acc,code in ms:
                    print(' ',kind,m[1],proto_desc(d,m[2]),'access',hex(acc),'code',hex(code))
                break

if __name__=='__main__': main()
