import unittest

from patch_club_badge_override import patch_smali_text
from verify_rebuilt_badge_override import verify_rebuilt_override


REPORT={
    'captured_registers':{'id':'v12','club':'v4','divisor':'v13'},
    'divisor_register_restored':True,
}

REBUILT='''
.method public static m_CreateClub([Ljava/lang/String;ILcom/newstargames/newstarsoccer/c_ArrayList10;Z)Lcom/newstargames/newstarsoccer/c_TClub;
    .registers 20

    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v13, 0xf
    rem-int/2addr v12, v13
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I

    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v13, 0xc45
    if-ne v12, v13, :cond_14e
    const/16 v12, 0x10
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
    goto :goto_166

    :cond_14e
    const/16 v13, 0xc55
    if-ne v12, v13, :cond_166
    const/16 v12, 0x11
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I

    :cond_166
    :goto_166
    const/16 v13, 0xf

    aget-object v12, p0, v6
.end method
'''

STOCK='''
.method public static m_CreateClub([Ljava/lang/String;)Lcom/newstargames/newstarsoccer/c_TClub;
    .registers 17
    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v13, 0xf
    rem-int/2addr v12, v13
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
    aget-object v8, v9, v13
.end method
'''


class RebuiltOverrideVerificationTests(unittest.TestCase):
    def test_accepts_baksmali_renamed_labels_and_checks_semantics(self):
        result=verify_rebuilt_override(REBUILT,REPORT)
        self.assertTrue(result['fallback_present'])
        self.assertTrue(result['club3141_branch_present'])
        self.assertTrue(result['club3157_branch_present'])
        self.assertTrue(result['divisor_restore_before_next_field_read'])
        self.assertEqual(result['badge_style_write_count'],3)

    def test_accepts_manifest_sized_override_set(self):
        mapping={3135:16,3141:17,3160:18,3163:19}
        patched,report=patch_smali_text(STOCK,overrides=mapping)
        result=verify_rebuilt_override(patched,report)
        self.assertEqual(result['override_count'],4)
        self.assertEqual(result['overrides'],mapping)
        self.assertEqual(result['badge_style_write_count'],5)
        self.assertTrue(result['divisor_restore_before_next_field_read'])

    def test_rejects_missing_restore(self):
        broken=REBUILT.replace('    const/16 v13, 0xf\n\n    aget-object v12, p0, v6','    aget-object v12, p0, v6',1)
        with self.assertRaises(ValueError):
            verify_rebuilt_override(broken,REPORT)

    def test_rejects_missing_conditional_branch_even_if_constants_exist(self):
        broken=REBUILT.replace('    if-ne v12, v13, :cond_14e\n','',1)
        with self.assertRaises(ValueError):
            verify_rebuilt_override(broken,REPORT)


if __name__=='__main__': unittest.main()
