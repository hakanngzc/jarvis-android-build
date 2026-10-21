#!/usr/bin/env python3
import hashlib,io,re,struct,sys,tempfile,zlib,zipfile
from pathlib import Path
from dex_inspect import Dex

if len(sys.argv)!=3:
    raise SystemExit('usage: patch_trial_skip_for_persistence_test.py INPUT_APK OUTPUT_APK')
src,dst=map(Path,sys.argv[1:])
MESSAGE='Lcom/newstargames/newstarsoccer/c_TScreen_Message;'
MAINMENU='Lcom/newstargames/newstarsoccer/c_TScreen_MainMenu;'
FROM='DoTrial1'
TO='TrialDone'

trial_patched=False
career_gate_patched=False
entries=[]
with zipfile.ZipFile(src,'r') as zin:
    for info in zin.infolist():
        data=zin.read(info.filename)
        if re.fullmatch(r'classes\d*\.dex',Path(info.filename).name):
            with tempfile.NamedTemporaryFile(suffix='.dex',delete=False) as f:
                f.write(data); name=f.name
            d=Dex(name)
            blob=bytearray(data)
            changed=False
            for kind,mid,mm,acc,code in d.class_methods(MAINMENU) or []:
                if mm[1]!='m_ButtonCareer' or not code: continue
                items=d.disasm(code)[-1]
                jumps=[off for off,op,args,raw in items if op=='if-nez']
                if len(jumps)!=1:
                    raise SystemExit(f'Expected one MainMenu Career if-nez, found {jumps}')
                off=jumps[0]
                pos=code+16+off*2
                unit=struct.unpack_from('<H',blob,pos)[0]
                next_unit=struct.unpack_from('<H',blob,pos+2)[0]
                if unit!=0x0039 or next_unit!=0x0008:
                    raise SystemExit(f'Unexpected Career gate encoding {unit:04x} {next_unit:04x}')
                struct.pack_into('<H',blob,pos,0x0029)
                changed=True; career_gate_patched=True
                print(f'Persistence test harness: {info.filename} MainMenu.m_ButtonCareer @{off:x}: if-nez -> goto/16 SaveSlot')
                break
            for kind,mid,mm,acc,code in d.class_methods(MESSAGE) or []:
                if mm[1]!='m_DoCallFunction' or not code: continue
                hits=[]
                for off,op,args,raw in d.disasm(code)[-1]:
                    if op=='const-string' and args==repr(FROM): hits.append(off)
                if len(hits)<2:
                    raise SystemExit(f'Expected >=2 {FROM} references in dispatcher, found {hits}')
                try: to_idx=d.strings.index(TO)
                except ValueError: raise SystemExit(f'{TO} missing from DEX string pool')
                if to_idx>0xffff: raise SystemExit('TrialDone string requires jumbo index')
                pos=code+16+(hits[0]+1)*2
                old=struct.unpack_from('<H',blob,pos)[0]
                if d.strings[old]!=FROM: raise SystemExit('const-string operand verification failed')
                struct.pack_into('<H',blob,pos,to_idx)
                changed=True; trial_patched=True
                print(f'Persistence test harness: {info.filename} Message.m_DoCallFunction @{hits[0]:x}: {FROM} -> {TO}')
                break
            if changed:
                blob[12:32]=hashlib.sha1(blob[32:]).digest()
                struct.pack_into('<I',blob,8,zlib.adler32(blob[12:]) & 0xffffffff)
                data=bytes(blob)
            Path(name).unlink(missing_ok=True)
        entries.append((info,data))

if not career_gate_patched: raise SystemExit('MainMenu Career FTUE gate was not patched')
if not trial_patched: raise SystemExit('Trial continuation was not patched')
with zipfile.ZipFile(dst,'w') as zout:
    for info,data in entries:
        zi=zipfile.ZipInfo(info.filename,info.date_time)
        zi.compress_type=info.compress_type; zi.comment=info.comment; zi.extra=info.extra
        zi.internal_attr=info.internal_attr; zi.external_attr=info.external_attr
        zi.create_system=info.create_system; zi.flag_bits=info.flag_bits
        zout.writestr(zi,data)
print(f'Wrote test-only persistence harness APK: {dst}')
