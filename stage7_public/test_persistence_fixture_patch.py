import unittest

from persistence_fixture_patch import patch_mutator_text, patch_verifier_text


PLAYER='Lcom/newstargames/newstarsoccer/c_TPlayer;'

MUTATOR_SRC='''.class public Lcom/newstargames/newstarsoccer/c_TPlayer;
.method public p_SaveCareer()I
    .locals 2
    const/4 v0, 0x1
    return v0
.end method

.method public p_Other()V
    .locals 1
    return-void
.end method
'''

VERIFIER_SRC='''.class public Lcom/newstargames/newstarsoccer/c_TPlayer;
.method public static m_LoadCareer()I
    .locals 3
    const/4 v0, 0x1
    return v0
.end method
'''


class PersistenceFixturePatchTests(unittest.TestCase):
    def test_mutator_injects_only_savecareer_and_preserves_stock_flow(self):
        out,meta=patch_mutator_text(MUTATOR_SRC)
        self.assertEqual(meta['method'],'p_SaveCareer')
        self.assertEqual(meta['return_type'],'I')
        self.assertIn('.locals 5',out)
        self.assertIn('const/16 v2, 0x10e1',out) # bank 4321
        self.assertIn(f'iput v2, p0, {PLAYER}->m_bank:I',out)
        self.assertIn('const/16 v2, 0x141',out) # wage 321
        self.assertIn(f'iput v2, p0, {PLAYER}->m_wage:I',out)
        self.assertIn(f'iput v2, p0, {PLAYER}->m_goalbonus:I',out)
        self.assertIn(f'iput v2, p0, {PLAYER}->m_assistbonus:I',out)
        self.assertIn(f'iput v2, p0, {PLAYER}->m_relationboss:F',out)
        self.assertIn(f'iput v2, p0, {PLAYER}->m_lastspendtimefriends:F',out)
        self.assertIn(f'iput v2, p0, {PLAYER}->m_spenttime:I',out)
        self.assertIn(f'iget-object v2, p0, {PLAYER}->m_technique:[I',out)
        self.assertIn('aput v4, v2, v3',out)
        self.assertIn('return v0',out)
        self.assertEqual(out.count('STAGE7_TEST_MUTATOR_BEGIN'),1)
        self.assertEqual(out.count('.method public p_Other()V'),1)

    def test_mutator_is_fail_closed_if_already_patched(self):
        out,_=patch_mutator_text(MUTATOR_SRC)
        with self.assertRaises(ValueError): patch_mutator_text(out)

    def test_verifier_resaves_before_preserving_unique_int_return(self):
        out,meta=patch_verifier_text(VERIFIER_SRC)
        self.assertEqual(meta['method'],'m_LoadCareer')
        self.assertEqual(meta['return_type'],'I')
        self.assertEqual(meta['return_register'],'v0')
        self.assertIn('.locals 4',out)
        self.assertIn('sget-object v3, Lcom/newstargames/newstarsoccer/bb_;->g_player:',out)
        self.assertIn(f'invoke-virtual {{v3}}, {PLAYER}->p_SaveCareer()I',out)
        self.assertIn('move-result v3',out)
        self.assertLess(out.index('STAGE7_TEST_VERIFY_RESAVE_BEGIN'),out.rindex('return v0'))
        self.assertEqual(out.count('return v0'),1)
        self.assertEqual(out.count('STAGE7_TEST_VERIFY_RESAVE_BEGIN'),1)

    def test_verifier_rejects_multiple_returns(self):
        bad=VERIFIER_SRC.replace('    return v0\n','    return v0\n    return v0\n')
        with self.assertRaises(ValueError): patch_verifier_text(bad)


if __name__=='__main__': unittest.main()
