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


class Stage4LiveInputSpeedTests(unittest.TestCase):
    def test_live_driver_avoids_duplicate_resume_decode_and_long_action_sleeps(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'stage4_live_input_speed')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)
        driver_start = prepared.index('drive_live_chance(){')
        driver_end = prepared.index("\n}\n", driver_start) + 3
        driver = prepared[driver_start:driver_end]
        self.assertEqual(1, driver.count('stage4_tools/find_match_resume.py'))
        self.assertNotIn('sleep 3', driver)
        self.assertIn('sleep 1', driver)
        self.assertLess(
            driver.index('stage4_tools/find_match_resume.py'),
            driver.index('stage4_tools/find_live_ball.py'),
        )
        self.assertLess(
            driver.index('stage4_tools/find_live_ball.py'),
            driver.index('stage4_tools/find_kick_ball.py'),
        )
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)


if __name__ == '__main__':
    unittest.main()
