import unittest
from verify_rebuilt_persistence_fixture import verify_mutator,verify_verifier

P='Lcom/newstargames/newstarsoccer/c_TPlayer;'
B='Lcom/newstargames/newstarsoccer/bb_;'

MUT='''.method public final p_SaveCareer()I
    .registers 11
    const/16 v7, 0x10e1
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_bank:I
    const/16 v7, 0x141
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_wage:I
    const/16 v7, 0x4d
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_goalbonus:I
    const/16 v7, 0x37
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_assistbonus:I
    const/16 v7, 0x3039
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_lasttransferdate:I
    const/16 v7, 0x3038
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_lastnegotiations:I
    const v7, 0x42750000    # 61.25f
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_relationboss:F
    const v7, 0x42850000    # 66.5f
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_relationsponsors:F
    const/4 v7, 0x7
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_spenttime:I
    const/4 v7, 0x3
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_gambling:I
    const/4 v8, 0x0
    const/16 v9, 0x47
    iget-object v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_technique:[I
    aput v9, v7, v8
    const/16 v9, 0x48
    iget-object v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_pace:[I
    aput v9, v7, v8
    const/16 v9, 0x49
    iget-object v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_vision:[I
    aput v9, v7, v8
    const/16 v9, 0x4a
    iget-object v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_setpieces:[I
    aput v9, v7, v8
    const/16 v9, 0x4b
    iget-object v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_power:[I
    aput v9, v7, v8
    const/4 v7, 0x5
    iput v7, p0, Lcom/newstargames/newstarsoccer/c_TPlayer;->m_donetraining:I
    return v2
.end method
'''

VER='''.method public static m_LoadCareer()I
    .registers 20
    const/4 v7, 0x1
    sget-object v19, Lcom/newstargames/newstarsoccer/bb_;->g_player:Lcom/newstargames/newstarsoccer/c_TPlayer;
    invoke-virtual/range {v19 .. v19}, Lcom/newstargames/newstarsoccer/c_TPlayer;->p_SaveCareer()I
    move-result v19
    return v7
.end method
'''

class RebuiltVerifierTests(unittest.TestCase):
    def test_mutator_accepts_commentless_rebuilt_semantics(self):
        r=verify_mutator(MUT,{'directive':'registers','new_registers':11})
        self.assertTrue(r['pass'],r)
        self.assertEqual(r['bank'],'4321')
        self.assertEqual(r['wage'],'321')
        self.assertEqual(r['skills'],[71,72,73,74,75])

    def test_mutator_rejects_wrong_value_even_when_field_exists(self):
        bad=MUT.replace('const/16 v7, 0x10e1','const/16 v7, 0x10e0',1)
        with self.assertRaises(ValueError): verify_mutator(bad,{'directive':'registers','new_registers':11})

    def test_verifier_accepts_resave_call_and_preserved_return(self):
        r=verify_verifier(VER,{'directive':'registers','new_registers':20,'return_register':'v7','scratch':'v19'})
        self.assertTrue(r['pass'],r)
        self.assertEqual(r['return_register'],'v7')

    def test_verifier_rejects_changed_original_return(self):
        bad=VER.replace('return v7','return v19')
        with self.assertRaises(ValueError): verify_verifier(bad,{'directive':'registers','new_registers':20,'return_register':'v7','scratch':'v19'})

if __name__=='__main__': unittest.main()
