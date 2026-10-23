#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import patch_club_badge_styles as clubpatch
import patch_shield_ui as uipatch
import generate_fixture_badges as badges


STOCK_SMALI = r'''
.class public Lcom/newstargames/newstarsoccer/c_TClub;
.super Lcom/newstargames/newstarsoccer/c_TBase_Team;

.method public static m_CreateClub([Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TClub;
    .locals 16

    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I

    const/16 v13, 0xf

    rem-int/2addr v12, v13

    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I

    aget-object v12, v6, v1
    return-object v4
.end method
'''

STOCK_UI = r'''Img:(Existing,NewGUI/Existing.png)
Macro:(A)
    Rect:(0,0,0,0)
        Selector(MatchColours,BadgeStyle1)
    {
        Rect:(0,0,0,0)
        Draw:(MapShieldDesign14,0,0,-105,142)
            TweenSize(-210,285,-50,50,3,-2)
        Draw:(MapShieldDesign15,0,0,-105,142)
            TweenSize(-210,285,-50,50,3,-2)
    }
EndM
Macro:(B)
    Rect:(0,0,0,0)
        Selector(MatchColours,BadgeStyle2)
    {
        Rect:(0,0,0,0)
        Draw:(MapShieldDesign15,4,5,-210,285)
            Handle(-100,100)
            TweenCol(#FFFFFF80)
    }
EndM
'''


class ClubBadgeStylePatchTests(unittest.TestCase):
    def test_two_target_ids_override_after_stock_modulo_and_fallback_is_kept(self):
        out = clubpatch.patch_text(STOCK_SMALI)
        self.assertIn('rem-int/2addr v12, v13', out)
        self.assertIn('const/16 v13, 0xc45', out)  # 3141
        self.assertIn('const/16 v12, 0x10', out)
        self.assertIn('const/16 v13, 0xc5b', out)  # 3163
        self.assertIn('const/16 v12, 0x11', out)
        self.assertIn(':reborn_badge_done', out)
        # Stock fallback is committed first; target clubs get one conditional overwrite.
        self.assertEqual(out.count('->m_badgestyle:I'), 3)
        self.assertIn('.locals 16', out)
        self.assertNotIn('.locals 17', out)
        # Do not introduce v16+, which compact iget/if formats cannot encode.
        self.assertNotRegex(out, r'\bv(?:1[6-9]|[2-9]\d)\b')

    def test_smali_patch_refuses_second_application(self):
        once = clubpatch.patch_text(STOCK_SMALI)
        with self.assertRaises(ValueError):
            clubpatch.patch_text(once)

    def test_smali_patch_refuses_ambiguous_stock_sites(self):
        doubled = STOCK_SMALI.replace('    return-object v4\n', STOCK_SMALI.split('.method',1)[1].split('.end method',1)[0] + '\n    return-object v4\n')
        with self.assertRaises(ValueError):
            clubpatch.patch_text(doubled)


class ShieldUiPatchTests(unittest.TestCase):
    def test_every_design15_child_is_cloned_as_styles_16_and_17(self):
        out = uipatch.patch_text(STOCK_UI)
        self.assertTrue(out.startswith('Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)\nImg:(RebornBadge3163,NewGUI/RebornBadges/3163.png)\n'))
        self.assertEqual(out.count('Draw:(RebornBadge3141'), 2)
        self.assertEqual(out.count('Draw:(RebornBadge3163'), 2)
        self.assertIn('Draw:(RebornBadge3141,0,0,-105,142)\n            TweenSize(-210,285,-50,50,3,-2)', out)
        self.assertIn('Draw:(RebornBadge3163,4,5,-210,285)\n            Handle(-100,100)\n            TweenCol(#FFFFFF80)', out)
        self.assertEqual(out.count('Draw:(MapShieldDesign15'), 2)

    def test_ui_patch_refuses_second_application(self):
        once = uipatch.patch_text(STOCK_UI)
        with self.assertRaises(ValueError):
            uipatch.patch_text(once)


class FixtureBadgeTests(unittest.TestCase):
    def test_generated_badges_are_distinct_rgba_images(self):
        with tempfile.TemporaryDirectory() as td:
            paths = badges.generate(Path(td))
            self.assertEqual(set(paths), {3141, 3163})
            raw = []
            for club_id, path in paths.items():
                im = Image.open(path).convert('RGBA')
                self.assertEqual(im.size, (192, 192))
                alpha = im.getchannel('A')
                self.assertLess(alpha.getextrema()[0], 255)
                self.assertGreater(alpha.getextrema()[1], 0)
                raw.append(path.read_bytes())
            self.assertNotEqual(raw[0], raw[1])


if __name__ == '__main__':
    unittest.main()
