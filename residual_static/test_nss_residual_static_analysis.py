import unittest
from nss_residual_static_analysis import canonical_screen, legacy_screen, classify_name

class Rules(unittest.TestCase):
    def test_legacy_misses_generic_gscreen_descendant(self):
        supers={
          'Lcom/newstargames/newstarsoccer/c_GScreen;':'Ljava/lang/Object;',
          'Lcom/newstargames/newstarsoccer/c_TScreen;':'Lcom/newstargames/newstarsoccer/c_GScreen;',
          'Lcom/newstargames/newstarsoccer/c_TScreen_Foo;':'Lcom/newstargames/newstarsoccer/c_TScreen;',
          'Lcom/newstargames/newstarsoccer/c_CustomOverlay;':'Lcom/newstargames/newstarsoccer/c_GScreen;',
        }
        self.assertTrue(legacy_screen('Lcom/newstargames/newstarsoccer/c_TScreen_Foo;'))
        self.assertFalse(legacy_screen('Lcom/newstargames/newstarsoccer/c_CustomOverlay;'))
        self.assertTrue(canonical_screen('Lcom/newstargames/newstarsoccer/c_CustomOverlay;',supers))
    def test_known_domain_name_is_not_catchall(self):
        self.assertEqual(classify_name('Lcom/newstargames/newstarsoccer/c_TContractOffer;'),'career_player')
        self.assertEqual(classify_name('Lcom/newstargames/newstarsoccer/c_XYZZY;'),'game_domain_other')
if __name__=='__main__': unittest.main()
