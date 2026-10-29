import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BASE = {
    'sdate': 12,
    'clubnationid': 62,
    'clubid': 952,
    'goalbonus': 1,
    'wage': 2,
    'lastnegotiations': 0,
    'lasttransferdate': 0,
    'playerrecordsha256': 'pre',
    'clubrecordsha256': 'c',
    'competitionrecordsha256': 'x',
    'additionalclubrecordsha256': 'a',
}
POST = {**BASE, 'sdate': 11, 'playerrecordsha256': 'post'}
RESTART = dict(POST)
FLOW = (
    'Create Screen: retirement\n'
    'QUICK SAVE\n'
    '>>>> RETIRED : 11130\n'
    'LoadCareer saveslot: 0\n'
    'SETTING ACTIVE: gamemenu\n'
)


class RetirementVerifierTests(unittest.TestCase):
    def test_valid_persistence_boundary_passes(self):
        mod = load_module(ROOT / 'stage2_residual_tools/verify_stage2_retirement_persistence.py', 'verify')
        result = mod.verify(BASE, POST, RESTART, b'abc', b'abc', FLOW)
        self.assertTrue(result['pass'])
        self.assertTrue(all(result['checks'].values()))

    def test_missing_stock_reload_marker_fails(self):
        mod = load_module(ROOT / 'stage2_residual_tools/verify_stage2_retirement_persistence.py', 'verify2')
        result = mod.verify(BASE, POST, RESTART, b'abc', b'abc', FLOW.replace('LoadCareer saveslot: 0\n', ''))
        self.assertFalse(result['pass'])
        self.assertFalse(result['checks']['loadcareer_marker'])

    def test_raw_save_drift_fails(self):
        mod = load_module(ROOT / 'stage2_residual_tools/verify_stage2_retirement_persistence.py', 'verify3')
        result = mod.verify(BASE, POST, RESTART, b'abc', b'abd', FLOW)
        self.assertFalse(result['pass'])
        self.assertFalse(result['checks']['raw_save_byte_identical'])

    def test_retired_marker_must_precede_restart_load(self):
        mod = load_module(ROOT / 'stage2_residual_tools/verify_stage2_retirement_persistence.py', 'verify4')
        wrong = (
            'Create Screen: retirement\nQUICK SAVE\n'
            'LoadCareer saveslot: 0\n>>>> RETIRED : 11130\nSETTING ACTIVE: gamemenu\n'
        )
        result = mod.verify(BASE, POST, RESTART, b'abc', b'abc', wrong)
        self.assertFalse(result['pass'])
        self.assertFalse(result['checks']['restart_marker_order'])

    def test_gamemenu_must_follow_restart_load(self):
        mod = load_module(ROOT / 'stage2_residual_tools/verify_stage2_retirement_persistence.py', 'verify5')
        result = mod.verify(BASE, POST, RESTART, b'abc', b'abc', FLOW.replace('SETTING ACTIVE: gamemenu\n', ''))
        self.assertFalse(result['pass'])
        self.assertFalse(result['checks']['gamemenu_after_load'])


if __name__ == '__main__':
    unittest.main()
