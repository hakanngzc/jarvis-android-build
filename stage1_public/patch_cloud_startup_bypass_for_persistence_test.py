#!/usr/bin/env python3
import hashlib,re,struct,sys,tempfile,zlib,zipfile
from pathlib import Path
from dex_inspect import Dex
if len(sys.argv)!=3: raise SystemExit('usage: patch_cloud_startup_bypass_for_persistence_test.py INPUT_APK OUTPUT_APK')
src,dst=map(Path,sys.argv[1:])
GAME='Lcom/newstargames/newstarsoccer/c_GameEngine;'; SCREEN='Lcom/newstargames/newstarsoccer/c_TScreen_CloudSetup;'; CLOUD='Lcom/newstargames/newstarsoccer/c_Cloud;'
STARTUP='m_GoToStartupScreen'; SETUP_INTERNAL='m_Setup_Internal'
entries=[]; found=False; changed=False
with zipfile.ZipFile(src,'r') as zin:
    for info in zin.infolist():
        data=zin.read(info.filename)
        if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
            with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f: f.write(data); tmp=Path(f.name)
            try:
                d=Dex(tmp); methods=[x for x in (d.class_methods(CLOUD) or []) if x[2][1]==SETUP_INTERNAL]
                if methods:
                    if found: raise SystemExit('c_Cloud.m_Setup_Internal found in multiple DEX files')
                    if len(methods)!=1 or not methods[0][4]: raise SystemExit(f'Expected one coded c_Cloud.m_Setup_Internal, found {len(methods)}')
                    code=methods[0][4]; items=d.disasm(code)[-1]; by={off:(op,args,raw) for off,op,args,raw in items}
                    required=(0x0b,0x0e,0x0f,0x11,0x13,0x17,0x19,0x1c,0x26)
                    if any(off not in by for off in required): raise SystemExit('Unexpected c_Cloud.m_Setup_Internal layout')
                    if by[0x0b][0]!='invoke-static' or 'Skn3CheckOnline;->IsOnline' not in str(by[0x0b][1]): raise SystemExit(f'Expected IsOnline @0b: {by[0x0b]}')
                    if by[0x0e][0]!='move-result': raise SystemExit(f'Expected IsOnline result @0e: {by[0x0e]}')
                    if by[0x17][0]!='sget' or 'm_CLD_GetRootConfig_Offline' not in str(by[0x17][1]): raise SystemExit(f'Expected offline state @17: {by[0x17]}')
                    if by[0x19][0]!='invoke-static' or 'c_Cloud;->m_SetState' not in str(by[0x19][1]): raise SystemExit(f'Expected offline SetState @19: {by[0x19]}')
                    if by[0x1c][0]!='invoke-static' or 'c_CatalogueManager;->m_Get' not in str(by[0x1c][1]): raise SystemExit(f'Expected CatalogueManager setup @1c: {by[0x1c]}')
                    if by[0x26][0]!='sput-boolean' or 'm_offlineModeActive' not in str(by[0x26][1]): raise SystemExit(f'Expected offline flag @26: {by[0x26]}')
                    pos=code+16+0x0f*2; unit0,unit1=struct.unpack_from('<HH',data,pos); blob=bytearray(data)
                    if (unit0,unit1)==(0x0038,0x0008):
                        struct.pack_into('<H',blob,pos,0x0029)
                        blob[12:32]=hashlib.sha1(blob[32:]).digest(); struct.pack_into('<I',blob,8,zlib.adler32(blob[12:]) & 0xffffffff)
                        data=bytes(blob); changed=True
                        print(f'Stage1 cloud harness: {info.filename} @0f if-eqz IsOnline -> goto/16 stock offline state @17')
                    elif (unit0,unit1)==(0x0029,0x0008): print('Stage1 cloud harness already present')
                    else: raise SystemExit(f'Unexpected Setup_Internal @0f: {unit0:04x} {unit1:04x}')
                    found=True
            finally: tmp.unlink(missing_ok=True)
        entries.append((info,data))
if not found: raise SystemExit(f'{CLOUD}->{SETUP_INTERNAL} was not found')
with zipfile.ZipFile(dst,'w') as zout:
    for info,data in entries:
        zi=zipfile.ZipInfo(info.filename,info.date_time); zi.compress_type=info.compress_type; zi.comment=info.comment; zi.extra=info.extra; zi.internal_attr=info.internal_attr; zi.external_attr=info.external_attr; zi.create_system=info.create_system; zi.flag_bits=info.flag_bits
        zout.writestr(zi,data)
verified_startup=verified_screen=verified_offline=False
with zipfile.ZipFile(dst,'r') as zout:
    for name in zout.namelist():
        if not re.fullmatch(r'classes\d*\.dex',Path(name).name): continue
        blob=zout.read(name)
        with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f: f.write(blob); tmp=Path(f.name)
        try:
            d=Dex(tmp)
            for _kind,_mid,mm,_acc,code in d.class_methods(GAME) or []:
                if mm[1]!=STARTUP or not code: continue
                text='\n'.join(f'{op} {args}' for _off,op,args,_raw in d.disasm(code)[-1])
                if 'c_TScreen_CloudSetup' not in text or 'm_SetUpScreen' not in text: raise SystemExit('startup no longer enters CloudSetup.SetUpScreen')
                if 'c_TScreen_MainMenu' in text: raise SystemExit('direct MainMenu startup bypass appeared')
                verified_startup=True
            for _kind,_mid,mm,_acc,code in d.class_methods(SCREEN) or []:
                if mm[1]!='m_Update' or not code: continue
                by={off:(op,args,raw) for off,op,args,raw in d.disasm(code)[-1]}
                if by.get(3,('','',''))[0]!='if-eqz' or by[3][2].lower()!='0038 0007': raise SystemExit(f'CloudSetup.m_Update is not stock: {by.get(3)}')
                if not any(off==0x0a and op=='invoke-static' and 'c_Cloud;->m_Update' in str(args) for off,op,args,_raw in d.disasm(code)[-1]): raise SystemExit('stock c_Cloud.m_Update call missing')
                verified_screen=True
            for _kind,_mid,mm,_acc,code in d.class_methods(CLOUD) or []:
                if mm[1]!=SETUP_INTERNAL or not code: continue
                by={off:(op,args,raw) for off,op,args,raw in d.disasm(code)[-1]}; got=by.get(0x0f)
                if not got or got[0]!='goto/16' or got[2].lower()!='0029 0008': raise SystemExit(f'offline branch mismatch: {got}')
                if by.get(0x17,('','',''))[0]!='sget' or 'm_CLD_GetRootConfig_Offline' not in str(by[0x17][1]): raise SystemExit('stock offline target missing')
                if by.get(0x1c,('','',''))[0]!='invoke-static' or 'c_CatalogueManager;->m_Get' not in str(by[0x1c][1]): raise SystemExit('CatalogueManager continuation changed')
                verified_offline=True
        finally: tmp.unlink(missing_ok=True)
if not (verified_startup and verified_screen and verified_offline): raise SystemExit(f'verification incomplete startup={verified_startup} screen={verified_screen} offline={verified_offline}')
print(f'VERIFIED_STAGE1_CLOUD_HARNESS=PASS state={"applied" if changed else "already-present"}')
