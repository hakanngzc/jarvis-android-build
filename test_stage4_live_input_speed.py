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

    def test_live_driver_scales_swipe_targets_to_current_rendered_frame(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'stage4_live_input_scaled')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)
        driver_start = prepared.index('drive_live_chance(){')
        driver_end = prepared.index("\n}\n", driver_start) + 3
        driver = prepared[driver_start:driver_end]
        self.assertIn('read -r kind x y frame_w frame_h <<<"$class"', driver)
        self.assertIn('target_x=$((frame_w / 2))', driver)
        self.assertIn('target_x=$((frame_w / 6))', driver)
        self.assertIn('target_x=$((frame_w * 5 / 6))', driver)
        self.assertIn('target_y=$((y - frame_h * 22 / 100))', driver)
        self.assertIn('target_y=$((y - frame_h * 29 / 100))', driver)
        self.assertNotIn('target_x=900', driver)
        self.assertNotIn('target_x=540', driver)
        self.assertNotIn('target_x=180', driver)

    def test_live_driver_gates_expensive_frame_decode_on_stock_match_events(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'stage4_live_input_log_gate')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)
        driver_start = prepared.index('drive_live_chance(){')
        driver_end = prepared.index("\n}\n", driver_start) + 3
        driver = prepared[driver_start:driver_end]
        self.assertIn('LIVE_EVENT_COUNT', driver)
        self.assertIn('LIVE_LAST_PROBE_EPOCH', driver)
        self.assertIn('matchminigame|tapball', driver)
        self.assertIn('event_count', driver)
        self.assertIn('probe_due', driver)
        self.assertIn('sleep 0.25', driver)
        self.assertLess(driver.index('event_count'), driver.index('capture_valid_live_frame "$frame"'))
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)


if __name__ == '__main__':
    unittest.main()
