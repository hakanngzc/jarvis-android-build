import unittest

from patch_club_badge_override import patch_smali_text


SAMPLE='''
.method public static m_CreateClub([Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TClub;
    .registers 17
    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v13, 0xf
    rem-int/2addr v12, v13
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
    aget-object v12, v16, v6
    invoke-static {v12}, Lcom/newstargames/newstarsoccer/bb_numberparser;->g_TryStrToInt(Ljava/lang/String;)I
    move-result v12
.end method
'''

ALT_REGISTERS='''
.method public static m_CreateClub([Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TClub;
    .registers 20
    iget v7, v2, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v11, 0xf
    rem-int/2addr v7, v11
    iput v7, v2, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
    aget-object v3, v18, v6
.end method
'''


class ClubBadgeOverrideTests(unittest.TestCase):
    def test_preserves_stock_fallback_and_overrides_only_two_ids(self):
        out,report=patch_smali_text(SAMPLE)
        self.assertEqual(report['anchor_count'],1)
        self.assertIn('rem-int/2addr v12, v13',out)
        self.assertIn('iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I',out)
        self.assertIn('const/16 v13, 0xc45',out)
        self.assertIn('const/16 v12, 0x10',out)
        self.assertIn('const/16 v13, 0xc55',out)
        self.assertIn('const/16 v12, 0x11',out)
        self.assertIn(':nss_reborn_badge_check_3157',out)
        self.assertIn(':nss_reborn_badge_done',out)
        self.assertEqual(out.count('->m_badgestyle:I'),3)
        self.assertLess(out.index('rem-int/2addr v12, v13'),out.index('const/16 v13, 0xc45'))
        self.assertLess(out.index(':nss_reborn_badge_done'),out.index('aget-object v12, v16, v6'))

    def test_anchor_follows_semantics_not_fixed_register_numbers(self):
        out,report=patch_smali_text(ALT_REGISTERS)
        self.assertEqual(report['anchor_count'],1)
        self.assertIn('rem-int/2addr v7, v11',out)
        self.assertIn('iget v7, v2, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I',out)
        self.assertIn('const/16 v11, 0xc45',out)
        self.assertIn('const/16 v7, 0x10',out)
        self.assertIn('const/16 v11, 0xc55',out)
        self.assertIn('const/16 v7, 0x11',out)
        self.assertIn('iput v7, v2, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I',out)

    def test_rejects_missing_or_multiple_stock_anchor(self):
        with self.assertRaises(ValueError):
            patch_smali_text('.method x\n.end method\n')
        with self.assertRaises(ValueError):
            patch_smali_text(SAMPLE+SAMPLE)


if __name__=='__main__': unittest.main()
