import json
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

from PIL import Image

from build_production_logo_apk import build_logo_assets

KEY='assets/monkey/NewGUI/Atlases/Key.key'
SHIELDS='assets/monkey/NewGUI/Screens/ShieldAnims.uih'
MAINMENU='assets/monkey/NewGUI/Screens/mainmenu.uis'
ONBOARD='assets/monkey/NewGUI/Screens/onboardingmain.uih'
CONSENT='assets/monkey/NewGUI/Screens/consent.uih'


def pascal_at(buf,s):
    raw=s.encode('ascii'); buf.append(len(raw)); buf.extend(raw)
    while len(buf)%4: buf.append(0)


def normal_record(buf,name):
    buf.extend(struct.pack('<I',0)); pascal_at(buf,name)
    buf.extend(struct.pack('<4H8f',16,16,16,16,0,0,0,0,16,16,1,1))


def synthetic_key():
    b=bytearray(struct.pack('<I',1))
    pascal_at(b,'UIAtlas1'); b.extend(struct.pack('<III',64,64,1)); normal_record(b,'Existing')
    b.extend(b'\x03Old\x08Existing\x00')
    return bytes(b)


SHIELD_TEXT='''
Selector(MatchColours,BadgeStyle1)
{
    Draw:(MapShieldDesign15,10,20,30,40)
        Handle(0,0)
}
Selector(MatchColours,BadgeStyle2)
{
    Draw:(MapShieldDesign15,50,60,70,80)
        TweenSize(1,1)
}
'''


class ProductionLogoApkTests(unittest.TestCase):
    def test_only_production_logo_assets_are_patched(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); logos=root/'logos'; logos.mkdir()
            for cid,color in ((3141,(10,20,30,255)),(3163,(200,100,20,255)),(3160,(20,80,210,255))):
                Image.new('RGBA',(80,100),color).save(logos/f'{cid}.png')
            manifest={
                'version':1,'cell_size':128,
                'clubs':[
                    {'club_id':3141,'style':16,'symbol':'REBORNClub3141','asset':'logos/3141.png'},
                    {'club_id':3160,'style':17,'symbol':'REBORNClub3160','asset':'logos/3160.png'},
                    {'club_id':3163,'style':18,'symbol':'REBORNClub3163','asset':'logos/3163.png'},
                ],
            }
            manifest_path=root/'logos.json'; manifest_path.write_text(json.dumps(manifest),encoding='utf-8')
            src=root/'base.apk'; out=root/'out.apk'; report=root/'report.json'
            untouched={MAINMENU:b'MAINMENU_STOCK',ONBOARD:b'ONBOARD_STOCK',CONSENT:b'CONSENT_STOCK'}
            with zipfile.ZipFile(src,'w') as z:
                z.writestr(KEY,synthetic_key())
                z.writestr(SHIELDS,SHIELD_TEXT)
                for name,data in untouched.items(): z.writestr(name,data)
                z.writestr('classes.dex',b'DEX-STOCK')
                z.writestr('META-INF/CERT.SF',b'old signature')
            result=build_logo_assets(src,out,manifest_path,root/'work',report,atlas_name='UIAtlas2')
            with zipfile.ZipFile(out) as z:
                names=set(z.namelist())
                self.assertIn('assets/monkey/NewGUI/Atlases/UIAtlas2.png',names)
                self.assertNotIn('META-INF/CERT.SF',names)
                for name,data in untouched.items(): self.assertEqual(z.read(name),data)
                self.assertEqual(z.read('classes.dex'),b'DEX-STOCK')
                shields=z.read(SHIELDS).decode('utf-8')
                for symbol in ('REBORNClub3141','REBORNClub3160','REBORNClub3163'):
                    self.assertIn(symbol,shields)
                self.assertNotIn('STAGE6_TEST_ONLY_LOGO_PROOF',shields)
            self.assertEqual(result['changed_members'],[
                KEY,SHIELDS,'assets/monkey/NewGUI/Atlases/UIAtlas2.png'
            ])
            self.assertEqual(result['club_count'],3)
            self.assertEqual(result['overrides'],{3141:16,3160:17,3163:18})
            self.assertTrue(result['forbidden_test_surfaces_preserved'])


if __name__=='__main__': unittest.main()
