#!/usr/bin/env python3
"""CI-only stock NSS 4.31 persistence hook.

Changes exactly one const-string operand inside c_TScreen_Message.m_DoCallFunction:
the trial-intro callback becomes StartCareer instead of DoTrial1. The real
StartCareer and p_SaveCareer implementations remain untouched. This file is
for hosted test builds only and is never a release modification.
"""
import hashlib
import re
import struct
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

from dex_inspect import Dex

TARGET_CLASS='Lcom/newstargames/newstarsoccer/c_TScreen_Message;'
TARGET_METHOD='m_DoCallFunction'
FROM='DoTrial1'
TO='StartCareer'


def fix_dex_header(b: bytearray) -> None:
    b[12:32]=hashlib.sha1(bytes(b[32:])).digest()
    struct.pack_into('<I',b,8,zlib.adler32(bytes(b[12:])) & 0xffffffff)


def patch_dex(blob: bytes):
    with tempfile.TemporaryDirectory(prefix='nss-ci-hook-dex-') as td:
        p=Path(td)/'classes.dex'; p.write_bytes(blob)
        d=Dex(p)
        try:
            to_idx=d.strings.index(TO)
        except ValueError:
            return blob,False,None
        if to_idx>0xffff:
            raise RuntimeError(f'{TO} string index requires jumbo encoding: {to_idx}')
        methods=d.class_methods(TARGET_CLASS) or []
        target=None
        for kind,mid,mm,acc,code in methods:
            if mm[1]==TARGET_METHOD:
                target=(code,d.disasm(code)[-1]); break
        if not target:
            return blob,False,None
        code,items=target
        hits=[(off,op,args,raw) for off,op,args,raw in items
              if op=='const-string' and args==repr(FROM)]
        if len(hits)<2:
            raise RuntimeError(f'Expected at least two {FROM} literals, found {len(hits)}')
        off,op,args,raw=hits[0]
        if not (0x110 <= off <= 0x140):
            raise RuntimeError(f'Unexpected trial-intro {FROM} offset: 0x{off:x}')
        b=bytearray(blob)
        operand=code+16+(off+1)*2
        old_idx=struct.unpack_from('<H',b,operand)[0]
        if d.strings[old_idx] != FROM:
            raise RuntimeError('DEX operand/string-table guard failed')
        struct.pack_into('<H',b,operand,to_idx)
        fix_dex_header(b)

        vp=Path(td)/'patched.dex'; vp.write_bytes(b); vd=Dex(vp)
        vm=[x for x in (vd.class_methods(TARGET_CLASS) or []) if x[2][1]==TARGET_METHOD]
        vitems=vd.disasm(vm[0][4])[-1]
        vals=[args for _,op,args,_ in vitems if op=='const-string' and args in (repr(FROM),repr(TO))]
        if repr(TO) not in vals or repr(FROM) not in vals:
            raise RuntimeError('Post-patch verification failed')
        return bytes(b),True,{'offset':off,'old_index':old_idx,'new_index':to_idx}


def patch_apk(src_path,out_path):
    changed=[]
    with zipfile.ZipFile(src_path,'r') as src, zipfile.ZipFile(out_path,'w',allowZip64=True) as out:
        for info in src.infolist():
            data=src.read(info.filename)
            if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
                data,did,meta=patch_dex(data)
                if did: changed.append((info.filename,meta))
            zi=zipfile.ZipInfo(info.filename,info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0))
            zi.external_attr=info.external_attr; zi.create_system=info.create_system
            out.writestr(zi,data,compress_type=info.compress_type,
                         compresslevel=9 if info.compress_type==zipfile.ZIP_DEFLATED else None)
    if len(changed)!=1:
        raise RuntimeError(f'Expected exactly one patched DEX, got {changed}')
    print(f'CI persistence hook: {changed[0][0]} offset=0x{changed[0][1]["offset"]:x} {FROM}->{TO}')


if __name__=='__main__':
    if len(sys.argv)!=3:
        raise SystemExit('usage: patch_career_test_hook.py INPUT_APK OUTPUT_APK')
    patch_apk(sys.argv[1],sys.argv[2])
