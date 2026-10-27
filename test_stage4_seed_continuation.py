import importlib.util
import unittest
from pathlib import Path


def load_module(path_str: str, name: str):
    path=Path(path_str)
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage4SeedContinuationTests(unittest.TestCase):
    def test_run290_seed_starts_at_cycle21_and_is_diagnostic_only(self):
        module=load_module(
            'stage4_tools/prepare_stage4_seed_continuation.py',
            'prepare_stage4_seed_continuation_test',
        )
        source=Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared=module.harden(source)
        self.assertIn('STAGE4_DIAGNOSTIC_SEED_XML',prepared)
        self.assertIn('STAGE4_DIAGNOSTIC_START_CYCLE',prepared)
        self.assertIn('DIAGNOSTIC ONLY: restoring verified natural cycle',prepared)
        self.assertIn('CYCLES="$DIAG_START_CYCLE"',prepared)
        self.assertIn('seq $((DIAG_START_CYCLE + 1)) "$MAX_MATCH_CYCLES"',prepared)
        self.assertIn('STAGE4_SEASONEND_DIAGNOSTIC_PASS',prepared)
        self.assertNotIn("echo 'STAGE4_NATURAL_SEASON_PASS'",prepared)
        self.assertNotIn("grep -q 'STAGE4_NATURAL_SEASON_PASS'",prepared)

    def test_diagnostic_still_requires_setup1_to_setup4_and_restart_equality(self):
        module=load_module(
            'stage4_tools/prepare_stage4_seed_continuation.py',
            'prepare_stage4_seed_continuation_requirements',
        )
        prepared=module.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))
        self.assertIn('for setup_n in 1 2 3 4',prepared)
        self.assertIn('post-season.json',prepared)
        self.assertIn('post-season-restart.json',prepared)
        self.assertIn("'restart_equal':not mismatches",prepared)
        self.assertIn("'diagnostic_only':True",prepared)
        for forbidden in ('m_sdate = 365','m_sdate=365','p_NewSeason(','m_skipMatches','m_Simulate'):
            self.assertNotIn(forbidden,prepared)


if __name__=='__main__':
    unittest.main()
