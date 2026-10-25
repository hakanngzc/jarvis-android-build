import unittest

from stage7_tools.patch_stage7_persistence_probe import build_probe_units, SENTINELS

class Stage7RuntimeProbePatchTests(unittest.TestCase):
    def test_sentinel_contract_covers_representative_families(self):
        for key in ('bank','lastnegotiations','items0','sponsors0','relationsponsors','relationboss','energy','technique0','deplete_technique','iapAgent1'):
            self.assertIn(key,SENTINELS)

    def test_probe_calls_stock_savecareer_and_returns(self):
        units=build_probe_units(100,{'m_bank':101,'m_lastnegotiations':102,'m_items':103,'m_sponsors':104,'m_relationsponsors':105,'m_relationboss':106,'m_energy':107,'m_technique':108,'m_deplete_technique':109,'m_iapAgent1':110},200)
        self.assertIn(0x106e,units)
        pos=units.index(0x106e)
        self.assertEqual(200,units[pos+1])
        self.assertEqual(0x000a,units[-2])
        self.assertEqual(0x000e,units[-1])
        self.assertGreater(len(units),20)

if __name__=='__main__':unittest.main()
