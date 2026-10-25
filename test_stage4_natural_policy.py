import importlib.util
import unittest
from pathlib import Path


def load_module(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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

    def test_prematch_preparer_requires_stock_play_hit_before_live_match(self):
        p = Path('stage4_tools/prepare_stage4_prematch.py')
        self.assertTrue(p.exists(), 'Stage4 prematch hardener must exist')
        module = load_module(str(p), 'prepare_stage4_prematch')
        prepared = module.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))
        self.assertIn("HitGadget: match.btn_Play", prepared)
        self.assertIn('prematch Play attempt $kickoff_attempt/4', prepared)
        self.assertIn('kickoff_hit=0', prepared)
        self.assertIn('could not register stock match.btn_Play after 4 attempts', prepared)
        self.assertNotIn('patch_stage4_new_season_probe.py', prepared)
        self.assertNotIn('m_skipMatches', prepared)
        self.assertNotIn('m_Simulate', prepared)

    def test_live_preparer_prioritizes_specific_resume_before_generic_green_marker(self):
        p = Path('stage4_tools/prepare_stage4_live_input.py')
        self.assertTrue(p.exists(), 'Stage4 live-input hardener must exist')
        module = load_module(str(p), 'prepare_stage4_live_input_resume_priority')
        prepared = module.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))
        resume = prepared.index('stage4_tools/find_match_resume.py')
        marker = prepared.index('stage4_tools/find_live_ball.py')
        kick = prepared.index('stage4_tools/find_kick_ball.py')
        self.assertLess(resume, marker)
        self.assertLess(resume, kick)
        self.assertIn('dismiss_interstitial_if_present "$step"', prepared)
        self.assertNotIn('m_skipMatches', prepared)
        self.assertNotIn('m_Simulate', prepared)

    def test_natural_workflow_actually_applies_prematch_preparer(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        self.assertIn('stage4_tools/prepare_stage4_short_league.py', text)
        self.assertIn('stage4_tools/prepare_stage4_prematch.py', text)
        self.assertIn('stage4-natural-gate.visual.sh', text)
        self.assertIn('stage4-natural-gate.shortleague.sh', text)
        self.assertIn('stage4-natural-gate.prematch.sh', text)
        self.assertIn(
            'python3 stage4_tools/prepare_stage4_short_league.py "$RUNNER_TEMP/stage4-natural-gate.visual.sh" "$RUNNER_TEMP/stage4-natural-gate.shortleague.sh"',
            text,
        )
        self.assertIn(
            'python3 stage4_tools/prepare_stage4_prematch.py "$RUNNER_TEMP/stage4-natural-gate.shortleague.sh" "$RUNNER_TEMP/stage4-natural-gate.prematch.sh"',
            text,
        )
        self.assertIn(
            'python3 stage4_tools/prepare_stage4_live_input.py "$RUNNER_TEMP/stage4-natural-gate.prematch.sh" "$RUNNER_TEMP/stage4-natural-gate.live.sh"',
            text,
        )
        self.assertIn('bash "$RUNNER_TEMP/stage4-natural-gate.live.sh"', text)


if __name__ == '__main__':
    unittest.main()
