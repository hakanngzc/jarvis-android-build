#!/usr/bin/env python3
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from append_logo_atlas import append_atlas

KEY='assets/monkey/NewGUI/Atlases/Key.key'
ATLAS='assets/monkey/NewGUI/Atlases/UIAtlas145.png'
SHIELDS='assets/monkey/NewGUI/Screens/ShieldAnims.uih'
MAINMENU='assets/monkey/NewGUI/Screens/mainmenu.uis'
ONBOARD='assets/monkey/NewGUI/Screens/onboardingmain.uih'
CONSENT='assets/monkey/NewGUI/Screens/consent.uih'


def sha(b): return hashlib.sha256(b).hexdigest()


def _supplemental_block(style,args,modifier,base_indent):
    carrier=base_indent+'Rect:(0,0,0,0)\n'+base_indent+'    Selector(MatchColours,'+style+')\n'+base_indent+'{\n'
    blanks=''.join(base_indent+'    Rect:(0,0,0,0)\n' for _ in range(16))
    body=(
        base_indent+f'    Draw:(REBORNClub3141,{args},,#FFFFFFFF)\n'+base_indent+'        '+modifier.strip()+'\n'+
        base_indent+f'    Draw:(REBORNClub3157,{args},,#FFFFFFFF)\n'+base_indent+'        '+modifier.strip()+'\n'
    )
    return carrier+blanks+body+base_indent+'}\n'


def extend_shield_selectors(text):
    # Match only the stock selector body itself. The inserted selector is a
    # separate sibling with 16 blank entries followed by styles 16 and 17, so
    # stock styles 0..15 remain byte-for-byte represented by the original block.
    selector=re.compile(
        r'(?P<selindent>^[ \t]*)Selector\(MatchColours,(?P<style>BadgeStyle[12])\)\r?\n'
        r'(?P<braceindent>^[ \t]*)\{\r?\n(?P<body>.*?)(?P<close>^[ \t]*\}\r?$)',
        re.M|re.S,
    )
    pos=0; pieces=[]; blocks=[]; matches=list(selector.finditer(text))
    for m in matches:
        body=m.group('body')
        dm=re.search(
            r'(?m)^(?P<drawindent>[ \t]*)Draw:\(MapShieldDesign15,(?P<args>[^\r\n)]*)\)\r?\n'
            r'(?P<modindent>[ \t]*)(?P<modifier>(?:TweenSize|Handle)\([^\r\n]*\))', body)
        if not dm:
            continue
        base_indent=m.group('braceindent')
        block=_supplemental_block(m.group('style'),dm.group('args'),dm.group('modifier'),base_indent)
        pieces.append(text[pos:m.end()]); pieces.append('\n'+block)
        blocks.append(block); pos=m.end()
    pieces.append(text[pos:])
    out=''.join(pieces)
    return out,{
        'selector_insert_count':len(blocks),
        'inserted_blocks':blocks,
        'stock_design15_count_before':text.count('Draw:(MapShieldDesign15,'),
        'stock_design15_count_after':out.count('Draw:(MapShieldDesign15,'),
    }


OVERLAY='''\n// STAGE6_TEST_ONLY_LOGO_PROOF_BEGIN\nDraw:(White,@L,@T,@W,@H,,#F6E9D2FF)\nDraw:(White,20,110,600,650,,#26354AFF)\nDraw:(White,26,116,588,638,,#FFF9EDFF)\nDraw:(REBORNClub3141,45,155,230,230,,#FFFFFFFF)\nDraw:(REBORNClub3157,365,155,230,230,,#FFFFFFFF)\nDraw:(MapShieldWhite,235,455,170,230,,#FFFFFFFF)\nDraw:(MapShieldDesign6,235,455,170,230,,#26354AFF)\nDraw:(MapShieldFrameAll,235,455,170,230,,#FFFFFFFF)\n// STAGE6_TEST_ONLY_LOGO_PROOF_END\n'''


def patch_mainmenu(text):
    if 'STAGE6_TEST_ONLY_LOGO_PROOF_BEGIN' in text:
        raise ValueError('runtime overlay already present')
    marker='M_Consent_Panel:()'
    if marker in text:
        out=text.replace(marker,OVERLAY+'\n'+marker,1)
    else:
        out=text+'\n'+OVERLAY
    return out,{'overlay_insert_count':1,'marker_found':marker in text}


def generate_logo_atlas(path):
    from PIL import Image, ImageDraw
    im=Image.new('RGBA',(256,128),(0,0,0,0)); d=ImageDraw.Draw(im)
    # ID 3141: black/white shield with a strong red identity marker.
    d.rounded_rectangle((10,8,118,120),radius=20,fill=(245,245,240,255),outline=(20,20,25,255),width=7)
    for x in (28,52,76,100): d.rectangle((x,16,x+10,112),fill=(20,20,25,255))
    d.ellipse((43,43,85,85),fill=(238,52,52,255),outline=(255,255,255,255),width=4)
    # ID 3157: yellow/blue circular crest, visually orthogonal to 3141.
    d.ellipse((140,10,244,118),fill=(250,205,35,255),outline=(20,65,170,255),width=8)
    d.rectangle((151,48,233,80),fill=(20,65,170,255))
    d.polygon([(192,20),(218,54),(192,108),(166,54)],fill=(245,245,240,255))
    d.ellipse((181,51,203,73),fill=(238,52,52,255))
    im.save(path)


def _zipinfo(info):
    zi=zipfile.ZipInfo(info.filename,info.date_time if info.date_time[0]>=1980 else (1980,1,1,0,0,0))
    zi.external_attr=info.external_attr; zi.create_system=info.create_system
    return zi


def is_signature(name):
    u=name.upper()
    return u=='META-INF/MANIFEST.MF' or (u.startswith('META-INF/') and u.endswith(('.SF','.RSA','.DSA','.EC')))


def build_fixture(src_apk,out_apk,work_dir,report_path):
    src_apk=Path(src_apk); out_apk=Path(out_apk); work=Path(work_dir); report_path=Path(report_path)
    work.mkdir(parents=True,exist_ok=True); report_path.parent.mkdir(parents=True,exist_ok=True)
    atlas_path=work/'UIAtlas145.png'; generate_logo_atlas(atlas_path); atlas_bytes=atlas_path.read_bytes()
    with zipfile.ZipFile(src_apk) as z:
        key=z.read(KEY); shields=z.read(SHIELDS).decode('utf-8-sig'); menu=z.read(MAINMENU).decode('utf-8-sig')
    records=[
        {'name':'REBORNClub3141','original_width':128,'original_height':128,'trimmed_width':128,'trimmed_height':128,
         'render_data':[0.0,1.0,0.0,1.0,1.0,0.0,0.5,0.0]},
        {'name':'REBORNClub3157','original_width':128,'original_height':128,'trimmed_width':128,'trimmed_height':128,
         'render_data':[0.0,1.0,0.5,1.0,1.0,0.0,1.0,0.0]},
    ]
    new_key,append_report=append_atlas(key,'UIAtlas145',256,128,records)
    new_shields,selector_report=extend_shield_selectors(shields)
    if selector_report['selector_insert_count'] < 1:
        raise ValueError('no BadgeStyle selector blocks patched')
    if selector_report['stock_design15_count_before']!=selector_report['stock_design15_count_after']:
        raise AssertionError('stock Design15 selector entries changed')
    new_menu,menu_report=patch_mainmenu(menu)
    replacements={
        KEY:new_key, ATLAS:atlas_bytes,
        SHIELDS:new_shields.encode('utf-8'), MAINMENU:new_menu.encode('utf-8'),
        ONBOARD:b'Rect:(0,0,0,0)\n    SetTweak(FirstPlayLocal,FirstPlayIncrement,4)\n',
        CONSENT:b'Macro:(M_Consent_Panel)\nEndM\nMacro:(M_Consent_Panel_ATT)\nEndM\n',
    }
    seen=set()
    with zipfile.ZipFile(src_apk) as zin, zipfile.ZipFile(out_apk,'w',allowZip64=True) as zout:
        for info in zin.infolist():
            n=info.filename
            if is_signature(n): continue
            data=replacements[n] if n in replacements else zin.read(n)
            if n in replacements: seen.add(n)
            zi=_zipinfo(info); c=zipfile.ZIP_STORED if n=='resources.arsc' else info.compress_type
            zout.writestr(zi,data,compress_type=c,compresslevel=9 if c==zipfile.ZIP_DEFLATED else None)
        for n,data in replacements.items():
            if n not in seen:
                zout.writestr(n,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
    report={
        'source_apk_sha256':sha(src_apk.read_bytes()),'patched_apk_sha256':sha(out_apk.read_bytes()),
        'key_sha256_before':sha(key),'key_sha256_after':sha(new_key),'atlas145_sha256':sha(atlas_bytes),
        'append':append_report,'selector':selector_report,'mainmenu':menu_report,
        'runtime_symbols':['REBORNClub3141','REBORNClub3157','MapShieldDesign6'],
        'stock_fallback_contract':'original MapShieldDesign1..15 selector entries preserved; supplemental styles 16/17 only',
    }
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"STAGE6_RUNTIME_FIXTURE=PASS selectors={selector_report['selector_insert_count']} atlas_count={append_report['new_atlas_count']} out={out_apk}")
    return report


def main():
    if len(sys.argv)!=5: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.apk WORK_DIR REPORT.json')
    build_fixture(*sys.argv[1:])

if __name__=='__main__': main()
