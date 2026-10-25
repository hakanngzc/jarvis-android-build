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


class Stage4MatchResolutionTests(unittest.TestCase):
    def test_lowres_surface_is_configured_before_new_process_and_state_neutral(self):
        boundary = load_module('stage4_tools/prepare_stage4_boundary_scope.py', 'boundary_for_resolution')
        resolution = load_module('stage4_tools/prepare_stage4_match_resolution.py', 'stage4_match_resolution')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = resolution.harden(boundary.harden(source))
        baseline = prepared.index('dump_save natural-baseline; checkpoint natural-baseline')
        resize = prepared.index('adb shell wm size 540x1140')
        restart = prepared.index('start_game natural-lowres')
        reload = prepared.index('load_existing natural-lowres')
        season_start = prepared.index('START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0')
        self.assertLess(baseline, resize)
        self.assertLess(resize, restart)
        self.assertLess(restart, reload)
        self.assertLess(reload, season_start)
        self.assertGreaterEqual(prepared.count("adb shell wm size 2>/dev/null | tr -d '\\r' | tail -1"), 2)
        # Run193 proved resizing a live NSS process can crash the async audio
        # loader, so the only resize must happen before this low-res start.
        self.assertEqual(1, prepared.count('adb shell wm size 540x1140'))
        self.assertNotIn('natural runtime render surface -> 540x1140', prepared)
        self.assertEqual(2, prepared.count('BASE_FLOW_BYTES="$(wc -c < "$FLOW")"'))
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_kick_detector_scales_large_ball_window_for_half_resolution(self):
        text = Path('stage4_tools/find_kick_ball.py').read_text(encoding='utf-8')
        self.assertIn('win = max(90, min(320, w // 4))', text)
        self.assertIn('stride = max(6, w // 54)', text)


if __name__ == '__main__':
    unittest.main()
