#!/usr/bin/env python3
import csv
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

KEY='assets/monkey/NewGUI/Atlases/Key.key'
UI='assets/monkey/NewGUI/Common/ShieldAnims.uih'
CLUBS='assets/monkey/MyData/v2025/Clubs.txt'
FIXTURES={3141:'assets/monkey/NewGUI/RebornBadges/3141.png',3163:'assets/monkey/NewGUI/RebornBadges/3163.png'}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def club_ids(raw: bytes):
    text=raw.decode('utf-8-sig')
    rows=list(csv.DictReader(io.StringIO(text), delimiter='\t'))
    out=[]
    for r in rows:
        x=str(r.get('id','')).strip()
        if x.isdigit(): out.append(int(x))
    return out


def verify(stock_apk, patched_apk, patched_smali):
    stock_apk=Path(stock_apk); patched_apk=Path(patched_apk); patched_smali=Path(patched_smali)
    with zipfile.ZipFile(stock_apk) as zs, zipfile.ZipFile(patched_apk) as zp:
        sn=set(zs.namelist()); pn=set(zp.namelist())
        for required in (KEY,UI,CLUBS,'classes3.dex'):
            if required not in sn or required not in pn:
                raise ValueError(f'missing required member: {required}')
        stock_key=zs.read(KEY); patched_key=zp.read(KEY)
        if stock_key != patched_key:
            raise ValueError('Key.key changed; packed stock atlas database must stay byte-identical')
        stock_ids=club_ids(zs.read(CLUBS)); patched_ids=club_ids(zp.read(CLUBS))
        if stock_ids != patched_ids:
            raise ValueError('numeric club ID sequence changed')
        if 3141 not in patched_ids or 3163 not in patched_ids:
            raise ValueError('target club IDs missing')
        fixture_assets=[]
        for club_id,member in FIXTURES.items():
            if member not in pn:
                raise ValueError(f'missing fixture badge asset {member}')
            if not zp.read(member):
                raise ValueError(f'empty fixture badge asset {member}')
            fixture_assets.append(club_id)
        ui=zp.read(UI).decode('utf-8-sig')
        counts={
            '3141':ui.count('Draw:(RebornBadge3141'),
            '3163':ui.count('Draw:(RebornBadge3163'),
        }
        if counts != {'3141':6,'3163':6}:
            raise ValueError(f'custom selector draw count mismatch: {counts}')
        if ui.count('Draw:(MapShieldDesign15') != 6:
            raise ValueError('stock Design15 fallback count changed')
        if ui.count('Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)') != 1:
            raise ValueError('3141 Img declaration mismatch')
        if ui.count('Img:(RebornBadge3163,NewGUI/RebornBadges/3163.png)') != 1:
            raise ValueError('3163 Img declaration mismatch')
        if zs.read('classes3.dex') == zp.read('classes3.dex'):
            raise ValueError('classes3.dex did not change')

    smali=patched_smali.read_text(encoding='utf-8')
    needed=(
        'rem-int/2addr v12, v13',
        'const/16 v13, 0xc45', 'const/16 v12, 0x10',
        'const/16 v13, 0xc5b', 'const/16 v12, 0x11',
        ':reborn_check_3163', ':reborn_badge_done',
    )
    missing=[x for x in needed if x not in smali]
    if missing:
        raise ValueError(f'patched c_TClub smali missing markers: {missing}')
    if '.locals 17' in smali or any(f'v{x}' in smali for x in range(16,32)):
        raise ValueError('unexpected high local register introduced')
    if smali.count('->m_badgestyle:I') < 3:
        raise ValueError('fallback plus two target badge-style writes not present')

    return {
        'key_key_unchanged':True,
        'key_key_sha256':sha(stock_key),
        'club_ids_unchanged':True,
        'numeric_club_count':len(stock_ids),
        'custom_draw_counts':counts,
        'stock_fallback_present':True,
        'fixture_assets':fixture_assets,
        'classes3_changed':True,
    }


def main():
    if len(sys.argv) not in (4,5):
        raise SystemExit(f'usage: {sys.argv[0]} STOCK.apk PATCHED.apk PATCHED_c_TClub.smali [REPORT.json]')
    r=verify(*sys.argv[1:4])
    if len(sys.argv)==5:
        Path(sys.argv[4]).write_text(json.dumps(r,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print('STAGE6_FIXTURE_STRUCTURE=PASS '+json.dumps(r,sort_keys=True))


if __name__=='__main__': main()
