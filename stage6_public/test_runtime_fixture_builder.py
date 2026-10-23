import unittest

from build_runtime_fixture import extend_shield_selectors, patch_mainmenu


SAMPLE='''Rect:(0,0,0,0)\n    ColReadout(MatchColours,Badge1Col2)\n    Selector(MatchColours,BadgeStyle1)\n{\n    Rect:(0,0,0,0)\n    Draw:(MapShieldDesign14,0,0,-105,142)\n        TweenSize(-210,285,-50,50,3,-2)\n    Draw:(MapShieldDesign15,0,0,-105,142)\n        TweenSize(-210,285,-50,50,3,-2)\n}\nDraw:(MapShieldFrameAll,0,0,-105,142)\n'''


class RuntimeFixtureBuilderTests(unittest.TestCase):
    def test_supplemental_selector_preserves_stock_block_and_adds_16_17(self):
        out,rep=extend_shield_selectors(SAMPLE)
        self.assertIn(SAMPLE.strip(), out.replace(rep['inserted_blocks'][0].strip(), '').strip())
        self.assertEqual(rep['selector_insert_count'],1)
        self.assertIn('Selector(MatchColours,BadgeStyle1)',rep['inserted_blocks'][0])
        self.assertEqual(rep['inserted_blocks'][0].count('Rect:(0,0,0,0)'),17)  # carrier + 16 blanks
        self.assertIn('Draw:(REBORNClub3141,0,0,-105,142,,#FFFFFFFF)',rep['inserted_blocks'][0])
        self.assertIn('Draw:(REBORNClub3157,0,0,-105,142,,#FFFFFFFF)',rep['inserted_blocks'][0])
        self.assertEqual(out.count('Draw:(MapShieldDesign15,0,0,-105,142)'),1)

    def test_mainmenu_overlay_contains_two_new_identities_and_stock_fallback(self):
        src='Draw:(Title_Sky,@L,@T,@W,@H)\nM_Consent_Panel:()\n'
        out,rep=patch_mainmenu(src)
        self.assertEqual(rep['overlay_insert_count'],1)
        self.assertIn('Draw:(REBORNClub3141',out)
        self.assertIn('Draw:(REBORNClub3157',out)
        self.assertIn('Draw:(MapShieldDesign6',out)
        self.assertLess(out.index('REBORNClub3141'),out.index('M_Consent_Panel:()'))


if __name__=='__main__': unittest.main()
