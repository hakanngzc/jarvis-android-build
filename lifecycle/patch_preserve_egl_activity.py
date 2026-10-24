#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from pathlib import Path

OLD='MonkeyGame'
NEW='RebornGame'
HELPER_ENTRY='classes4.dex'


def rewrite_manifest_activity(data: bytes) -> tuple[bytes,int]:
    if len(OLD)!=len(NEW):
        raise AssertionError('activity replacement must stay byte-length compatible')
    count=0
    out=data
    for old,new in ((OLD.encode('utf-8'),NEW.encode('utf-8')),
                    (OLD.encode('utf-16le'),NEW.encode('utf-16le'))):
        hits=out.count(old)
        if hits:
            out=out.replace(old,new)
            count+=hits
    if count!=1:
        raise ValueError(f'expected exactly one MonkeyGame manifest string replacement, found {count}')
    if len(out)!=len(data):
        raise ValueError('manifest byte length changed')
    return out,count


def patch_apk_bytes(apk_bytes: bytes, helper_dex: bytes) -> tuple[bytes,dict]:
    source_sha=hashlib.sha256(apk_bytes).hexdigest()
    existing=[]
    manifest_count=0
    output=io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(apk_bytes),'r') as zin:
        names=zin.namelist()
        existing=sorted(n for n in names if re.fullmatch(r'classes\d*\.dex',Path(n).name))
        if HELPER_ENTRY in names:
            raise ValueError(f'{HELPER_ENTRY} already exists; refusing overwrite')
        if 'AndroidManifest.xml' not in names:
            raise ValueError('AndroidManifest.xml missing')
        with zipfile.ZipFile(output,'w') as zout:
            for info in zin.infolist():
                data=zin.read(info.filename)
                if info.filename=='AndroidManifest.xml':
                    data,manifest_count=rewrite_manifest_activity(data)
                zi=zipfile.ZipInfo(info.filename,info.date_time)
                zi.compress_type=info.compress_type
                zi.comment=info.comment; zi.extra=info.extra
                zi.internal_attr=info.internal_attr; zi.external_attr=info.external_attr
                zi.create_system=info.create_system; zi.flag_bits=info.flag_bits
                zout.writestr(zi,data)
            helper_info=zipfile.ZipInfo(HELPER_ENTRY)
            helper_info.compress_type=zipfile.ZIP_DEFLATED
            zout.writestr(helper_info,helper_dex)
    patched=output.getvalue()
    evidence={
        'source_apk_sha256':source_sha,
        'output_apk_sha256':hashlib.sha256(patched).hexdigest(),
        'helper_dex_sha256':hashlib.sha256(helper_dex).hexdigest(),
        'helper_dex_entry':HELPER_ENTRY,
        'existing_dex_entries':existing,
        'manifest_replacements':manifest_count,
        'activity_from':'MonkeyGame',
        'activity_to':'RebornGame',
        'existing_dex_payloads_rewritten':False,
    }
    return patched,evidence


def main() -> int:
    ap=argparse.ArgumentParser(description='Inject RebornGame EGL-preservation shim without rewriting stock DEX payloads')
    ap.add_argument('input_apk',type=Path)
    ap.add_argument('helper_dex',type=Path)
    ap.add_argument('output_apk',type=Path)
    ap.add_argument('--evidence',type=Path,required=True)
    a=ap.parse_args()
    patched,evidence=patch_apk_bytes(a.input_apk.read_bytes(),a.helper_dex.read_bytes())
    a.output_apk.parent.mkdir(parents=True,exist_ok=True); a.output_apk.write_bytes(patched)
    a.evidence.parent.mkdir(parents=True,exist_ok=True)
    a.evidence.write_text(json.dumps({'schema':1,'patch':evidence,'verdict':'LIFECYCLE_PRESERVE_EGL_ACTIVITY_PATCH_APPLIED'},indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('STOCK_DEX_PAYLOADS_REWRITTEN=false')
    print('ACTIVITY_SHIM=RebornGame')
    print('VERDICT=LIFECYCLE_PRESERVE_EGL_ACTIVITY_PATCH_APPLIED')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
