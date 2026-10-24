import unittest
from pathlib import Path


class Stage4NaturalSeasonPolicyTests(unittest.TestCase):
    def test_natural_gate_exists_and_forbids_boundary_seeding(self):
        p = Path('stage4_natural_season_gate.sh')
        self.assertTrue(p.exists(), 'natural season gate must exist')
        text = p.read_text(encoding='utf-8')
        forbidden = (
            'patch_stage4_new_season_probe.py',
            'm_sdate = 365',
            'm_sdate=365',
            'p_NewSeason(',
            'STAGE4_PROBE_PLAYMATCHES',
            'm_skipMatches',
            'm_Simulate',
            'patch_stage3_fast_match_probe.py',
        )
        for token in forbidden:
            self.assertNotIn(token, text, f'natural season gate must not use {token}')

    def test_natural_gate_requires_long_progression_and_reload(self):
        text = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        for required in (
            'natural_match_cycle',
            'MIN_PROGRESS_DAYS',
            'NewSeasonSetUp1',
            'NewSeasonSetUp2',
            'NewSeasonSetUp3',
            'NewSeasonSetUp4',
            'post-season-restart',
            'STAGE4_NATURAL_SEASON_PASS',
            'fatal_check',
        ):
            self.assertIn(required, text)


if __name__ == '__main__':
    unittest.main()
