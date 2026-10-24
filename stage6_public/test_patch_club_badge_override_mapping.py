import unittest

from patch_club_badge_override import patch_smali_text


SAMPLE = '''
.method public static m_CreateClub([Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TClub;
    .registers 17
    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v13, 0xf
    rem-int/2addr v12, v13
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
    aget-object v12, v16, v6
.end method
'''


class ClubBadgeOverrideMappingTests(unittest.TestCase):
    def test_accepts_arbitrary_mapping_while_preserving_stock_fallback(self):
        mapping = {3135: 16, 3141: 17, 3160: 18, 3163: 19}
        out, report = patch_smali_text(SAMPLE, overrides=mapping)
        self.assertEqual(report['overrides'], mapping)
        self.assertEqual(report['override_count'], 4)
        self.assertIn('rem-int/2addr v12, v13', out)
        for club_id, style in mapping.items():
            self.assertIn(hex(club_id), out)
            self.assertIn(hex(style), out)
        self.assertEqual(out.count('->m_badgestyle:I'), 1 + len(mapping))
        self.assertIn('const/16 v13, 0xf', out[out.index(':nss_reborn_badge_done'):])
        self.assertTrue(report['divisor_register_restored'])

    def test_mapping_order_is_deterministic(self):
        one, _ = patch_smali_text(SAMPLE, overrides={3163: 19, 3135: 16, 3160: 18, 3141: 17})
        two, _ = patch_smali_text(SAMPLE, overrides={3135: 16, 3141: 17, 3160: 18, 3163: 19})
        self.assertEqual(one, two)

    def test_rejects_duplicate_stock_range_and_invalid_values(self):
        with self.assertRaises(ValueError):
            patch_smali_text(SAMPLE, overrides={3141: 15})
        with self.assertRaises(ValueError):
            patch_smali_text(SAMPLE, overrides={0: 16})
        with self.assertRaises(ValueError):
            patch_smali_text(SAMPLE, overrides={3141: -1})
        with self.assertRaises(ValueError):
            patch_smali_text(SAMPLE, overrides={3141: 16, 3157: 16})


if __name__ == '__main__':
    unittest.main()
