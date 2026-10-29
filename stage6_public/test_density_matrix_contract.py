import unittest
from density_matrix_contract import CASES, validate_case

EXPECTED = {
    'tvdpi': {'api':29,'dpi':213,'density_split':'config.tvdpi.apk','language_split':'config.tr.apk'},
    'xhdpi': {'api':29,'dpi':320,'density_split':'config.xhdpi.apk','language_split':'config.en.apk'},
    'xxhdpi': {'api':34,'dpi':480,'density_split':'config.xxhdpi.apk','language_split':'config.tr.apk'},
    'xxxhdpi': {'api':34,'dpi':640,'density_split':'config.xxxhdpi.apk','language_split':''},
}

class DensityMatrixContractTests(unittest.TestCase):
    def test_exact_matrix_contract(self):
        self.assertEqual(CASES, EXPECTED)
        self.assertEqual({v['api'] for v in CASES.values()},{29,34})
        self.assertEqual({v['density_split'] for v in CASES.values()},
                         {'config.tvdpi.apk','config.xhdpi.apk','config.xxhdpi.apk','config.xxxhdpi.apk'})
        self.assertIn('', {v['language_split'] for v in CASES.values()})
        self.assertIn('config.tr.apk', {v['language_split'] for v in CASES.values()})
        self.assertIn('config.en.apk', {v['language_split'] for v in CASES.values()})

    def test_validate_case_rejects_drift(self):
        self.assertTrue(validate_case('xhdpi',29,320,'config.xhdpi.apk','config.en.apk'))
        with self.assertRaises(ValueError):
            validate_case('xhdpi',29,480,'config.xhdpi.apk','config.en.apk')

if __name__=='__main__': unittest.main()
