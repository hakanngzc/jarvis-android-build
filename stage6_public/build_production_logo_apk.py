#!/usr/bin/env python3
import hashlib
import json
import sys
import zipfile
from pathlib import Path

from production_logo_pipeline import (
    append_manifest_atlas,
    build_style_overrides,
    extend_shield_selectors,
    load_manifest,
    pack_logo_atlas,
)

KEY='assets/monkey/NewGUI/Atlases/Key.key'
SHIELDS='assets/monkey/NewGUI/Screens/ShieldAnims.uih'
MAINMENU='assets/monkey/NewGUI/Screens/mainmenu.uis'
ONBOARD='assets/monkey/NewGUI/Screens/onboardingmain.uih'
CONSENT='assets/monkey/NewGUI/Screens/consent.uih'
FORBIDDEN_TEST_SURFACES=(MAINMENU,ONBOARD,CONSENT)


def sha(data): return hashlib.sha256(data).hexdigest()


def is_signature(name):
    u=name.upper()
    return u=='META-INF/MANIFEST.MF' or (u.startswith('META-INF/') and u.endswith(('.SF','.RSA','.DSA','.EC')))


def _zipinfo(info):
    zi=zipfile.ZipInfo(info.filename,info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0))
    zi.external_attr=info.external_attr; zi.create_system=info.create_system
    return zi


def build_logo_assets(src_apk,out_apk,manifest_path,work_dir,report_path,atlas_name='UIAtlas145'):
    src_apk=Path(src_apk); out_apk=Path(out_apk); work=Path(work_dir); report_path=Path(report_path)
    if not src_apk.is_file(): raise ValueError(f'base APK not found: {src_apk}')
    if not atlas_name.startswith('UIAtlas') or not atlas_name[7:].isdigit():
        raise ValueError('atlas_name must use UIAtlas<number> form')
    manifest=load_manifest(manifest_path,require_assets=True)
    work.mkdir(parents=True,exist_ok=True); report_path.parent.mkdir(parents=True,exist_ok=True)
    atlas_path=work/f'{atlas_name}.png'
    layout=pack_logo_atlas(manifest,atlas_path)
    atlas_bytes=atlas_path.read_bytes()

    with zipfile.ZipFile(src_apk) as zin:
        names=set(zin.namelist())
        if KEY not in names or SHIELDS not in names:
            raise ValueError('base APK missing Stage6 Key.key or ShieldAnims.uih')
        if f'assets/monkey/NewGUI/Atlases/{atlas_name}.png' in names:
            raise ValueError(f'atlas already exists in base APK: {atlas_name}')
        key_before=zin.read(KEY)
        shields_before=zin.read(SHIELDS)
        forbidden_before={n:zin.read(n) for n in FORBIDDEN_TEST_SURFACES if n in names}

    key_after,append_report=append_manifest_atlas(key_before,manifest,atlas_name)
    shields_text=shields_before.decode('utf-8-sig')
    shields_after_text,selector_report=extend_shield_selectors(shields_text,manifest)
    shields_after=shields_after_text.encode('utf-8')
    atlas_member=f'assets/monkey/NewGUI/Atlases/{atlas_name}.png'
    replacements={KEY:key_after,SHIELDS:shields_after}

    out_apk.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(src_apk) as zin, zipfile.ZipFile(out_apk,'w',allowZip64=True) as zout:
        for info in zin.infolist():
            n=info.filename
            if is_signature(n): continue
            data=replacements[n] if n in replacements else zin.read(n)
            zi=_zipinfo(info)
            c=zipfile.ZIP_STORED if n=='resources.arsc' else info.compress_type
            zout.writestr(zi,data,compress_type=c,compresslevel=9 if c==zipfile.ZIP_DEFLATED else None)
        zout.writestr(atlas_member,atlas_bytes,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

    with zipfile.ZipFile(out_apk) as zout:
        out_names=set(zout.namelist())
        forbidden_after={n:zout.read(n) for n in FORBIDDEN_TEST_SURFACES if n in out_names}
        if forbidden_before != forbidden_after:
            raise AssertionError('production logo builder modified a forbidden test/UI surface')
        if any(is_signature(n) for n in out_names):
            raise AssertionError('stale APK signature survived production asset rewrite')
        if zout.read(KEY)!=key_after or zout.read(SHIELDS)!=shields_after or zout.read(atlas_member)!=atlas_bytes:
            raise AssertionError('production replacements did not round-trip')

    overrides=build_style_overrides(manifest)
    report={
        'source_apk_sha256':sha(src_apk.read_bytes()),
        'patched_apk_sha256':sha(out_apk.read_bytes()),
        'manifest':str(Path(manifest_path)),
        'club_count':len(overrides),
        'overrides':overrides,
        'atlas_name':atlas_name,
        'atlas_member':atlas_member,
        'atlas_sha256':sha(atlas_bytes),
        'atlas_layout':layout,
        'key_sha256_before':sha(key_before),'key_sha256_after':sha(key_after),
        'shields_sha256_before':sha(shields_before),'shields_sha256_after':sha(shields_after),
        'append':append_report,
        'selector':selector_report,
        'changed_members':[KEY,SHIELDS,atlas_member],
        'forbidden_test_surfaces_preserved':True,
        'test_overlay_present':False,
        'stock_fallback_contract':'styles 0..15 remain stock; manifest styles start at 16',
    }
    report_path.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f"STAGE6_PRODUCTION_ASSETS=PASS clubs={len(overrides)} atlas={atlas_name} test_surfaces_preserved=true")
    return report


def main():
    if len(sys.argv) not in (6,7):
        raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.apk MANIFEST.json WORK_DIR REPORT.json [ATLAS_NAME]')
    atlas=sys.argv[6] if len(sys.argv)==7 else 'UIAtlas145'
    build_logo_assets(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5],atlas_name=atlas)


if __name__=='__main__': main()
