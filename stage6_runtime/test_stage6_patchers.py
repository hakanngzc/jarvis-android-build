#!/usr/bin/env python3
import re
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
        ColReadout(MatchColours,Badge1Col2)
        Selector(MatchColours,BadgeStyle1)
    {
        Rect:(0,0,0,0)
        Draw:(MapShieldDesign14,0,0,-105,142)
            TweenSize(-210,285,-50,50,3,-2)
        Draw:(MapShieldDesign15,0,0,-105,142)
            TweenSize(-210,285,-50,50,3,-2)
    }
    Draw:(MapShieldFrameAll,0,0,-105,142)
EndM
Macro:(B)
    Rect:(0,0,0,0)
        ColReadout(MatchColours,Badge2Col2)
        Selector(MatchColours,BadgeStyle2)
    {
        Rect:(0,0,0,0)
        Draw:(MapShieldDesign15,4,5,-210,285)
            Handle(-100,100)
            TweenCol(#FFFFFF80)
    }
    Draw:(MapShieldFrameAll,0,0,-210,285)
EndM
'''


def selector_blocks(text):
    out=[]
    for m in re.finditer(r'Selector\(MatchColours,BadgeStyle([12])\)\s*\n\s*\{',text):
        brace=text.find('{',m.start()); depth=0; i=brace
        while i<len(text):
            if text[i]=='{': depth+=1
            elif text[i]=='}':
                depth-=1
                if depth==0:
                    out.append((m.group(1),text[m.start():i+1])); break
            i+=1
    return out


class ClubBadgeStylePatchTests(unittest.TestCase):
    def test_two_target_ids_override_after_stock_modulo_and_fallback_is_kept(self):
        out = clubpatch.patch_text(STOCK_SMALI)
        self.assertIn('rem-int/2addr v12, v13', out)
        self.assertIn('const/16 v13, 0xc45', out)
        self.assertIn('const/16 v12, 0x10', out)
        self.assertIn('const/16 v13, 0xc5b', out)
        self.assertIn('const/16 v12, 0x11', out)
        self.assertIn(':reborn_badge_done', out)
        self.assertEqual(out.count('->m_badgestyle:I'), 3)
        self.assertIn('.locals 16', out)
        self.assertNotIn('.locals 17', out)
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
    def test_custom_styles_use_separate_untinted_overlay_selectors(self):
        out = uipatch.patch_text(STOCK_UI)
        self.assertTrue(out.startswith('Img:(RebornBadge3141,NewGUI/RebornBadges/3141.png)\nImg:(RebornBadge3163,NewGUI/RebornBadges/3163.png)\n'))
        self.assertEqual(out.count('Draw:(RebornBadge3141'), 2)
        self.assertEqual(out.count('Draw:(RebornBadge3163'), 2)
        self.assertEqual(out.count('// STAGE6_REAL_LOGO_OVERLAY BadgeStyle'), 2)
        self.assertEqual(out.count('Draw:(MapShieldDesign15'), 2)

        blocks=selector_blocks(out)
        self.assertEqual(len(blocks),4)
        stock=[b for _,b in blocks if 'MapShieldDesign15' in b]
        overlays=[b for _,b in blocks if 'RebornBadge3141' in b or 'RebornBadge3163' in b]
        self.assertEqual(len(stock),2)
        self.assertEqual(len(overlays),2)
        for b in stock:
            self.assertNotIn('RebornBadge3141',b)
            self.assertNotIn('RebornBadge3163',b)
        for b in overlays:
            self.assertNotIn('MapShieldDesign15',b)
            self.assertIn('RebornBadge3141',b)
            self.assertIn('RebornBadge3163',b)
            # styles 0..15 are no-op children; styles 16/17 are the two raw images.
            self.assertGreaterEqual(b.count('Rect:(0,0,0,0)'),16)

        self.assertIn('Draw:(RebornBadge3141,0,0,-105,142)\n            TweenSize(-210,285,-50,50,3,-2)', out)
        self.assertIn('Draw:(RebornBadge3163,4,5,-210,285)\n            Handle(-100,100)\n            TweenCol(#FFFFFF80)', out)

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
