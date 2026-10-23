#!/usr/bin/env python3
import tempfile
import unittest
import zipfile
from pathlib import Path

import verify_fixture_apk as v

CLUBS = (
    'id\tshortname\tnationid\tleagueid\n'
    '3141\tBesiktas\t193\t7270\n'
    '3163\tGalatasaray\t193\t7270\n'
    '3157\tFenerbahce\t193\t7270\n'
).encode()

STOCK_UI = ('Selector(MatchColours,BadgeStyle1)\nDraw:(MapShieldDesign15,0,0,1,1)\n' * 4 +
            'Selector(MatchColours,BadgeStyle2)\nDraw:(MapShieldDesign15,0,0,1,1)\n' * 2).encode()
PATCHED_UI = (
    b'Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)\n'
    b'Img:(RebornBadge3163,NewGUI/RebornBadges/3163.png)\n' +
    STOCK_UI.replace(b'Draw:(MapShieldDesign15,0,0,1,1)',
                     b'Draw:(MapShieldDesign15,0,0,1,1)\nDraw:(RebornBadge3141,0,0,1,1)\nDraw:(RebornBadge3163,0,0,1,1)')
)
PATCHED_SMALI = '''
.locals 16
iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
const/16 v13, 0xf
rem-int/2addr v12, v13
iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
const/16 v13, 0xc45
const/16 v12, 0x10
iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
:reborn_check_3163
const/16 v13, 0xc5b
const/16 v12, 0x11
iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
:reborn_badge_done
'''


def make_apk(path: Path, *, patched=False, mutate_key=False, mutate_clubs=False):
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('classes3.dex', b'patched-dex' if patched else b'stock-dex')
        z.writestr('assets/monkey/NewGUI/Atlases/Key.key', b'KEY-CHANGED' if mutate_key else b'KEY-STOCK')
        z.writestr('assets/monkey/NewGUI/Screens/ShieldAnims.uih', PATCHED_UI if patched else STOCK_UI)
        z.writestr('assets/monkey/MyData/v2025/Clubs.txt', CLUBS.replace(b'3141', b'9999', 1) if mutate_clubs else CLUBS)
        if patched:
            z.writestr('assets/monkey/NewGUI/RebornBadges/3141.png', b'PNG-A')
            z.writestr('assets/monkey/NewGUI/RebornBadges/3163.png', b'PNG-B')


class VerifyFixtureApkTests(unittest.TestCase):
    def test_valid_fixture_passes_and_preserves_stock_identity_assets(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); stock=td/'stock.apk'; patched=td/'patched.apk'; smali=td/'c_TClub.smali'
            make_apk(stock); make_apk(patched, patched=True); smali.write_text(PATCHED_SMALI)
            r = v.verify(stock, patched, smali)
            self.assertTrue(r['key_key_unchanged'])
            self.assertTrue(r['club_ids_unchanged'])
            self.assertEqual(r['custom_draw_counts'], {'3141': 6, '3163': 6})
            self.assertTrue(r['stock_fallback_present'])
            self.assertEqual(r['fixture_assets'], [3141, 3163])

    def test_key_key_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); stock=td/'stock.apk'; patched=td/'patched.apk'; smali=td/'c_TClub.smali'
            make_apk(stock); make_apk(patched, patched=True, mutate_key=True); smali.write_text(PATCHED_SMALI)
            with self.assertRaises(ValueError): v.verify(stock, patched, smali)

    def test_club_id_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); stock=td/'stock.apk'; patched=td/'patched.apk'; smali=td/'c_TClub.smali'
            make_apk(stock); make_apk(patched, patched=True, mutate_clubs=True); smali.write_text(PATCHED_SMALI)
            with self.assertRaises(ValueError): v.verify(stock, patched, smali)

    def test_missing_custom_asset_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            td = Path(td); stock=td/'stock.apk'; patched=td/'patched.apk'; smali=td/'c_TClub.smali'
            make_apk(stock); make_apk(patched, patched=True); smali.write_text(PATCHED_SMALI)
            tmp=td/'tmp.apk'
            with zipfile.ZipFile(patched) as zin, zipfile.ZipFile(tmp,'w') as zout:
                for info in zin.infolist():
                    if info.filename.endswith('/3163.png'): continue
                    zout.writestr(info, zin.read(info.filename))
            tmp.replace(patched)
            with self.assertRaises(ValueError): v.verify(stock, patched, smali)


if __name__ == '__main__': unittest.main()
