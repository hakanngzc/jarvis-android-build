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
    def composed_gate(self):
        stage2 = load_module('stage2_residual_tools/prepare_stage2_gate.py', 'stage2_for_stage4_resolution')
        event = load_module('stage4_tools/prepare_stage4_event_navigation.py', 'events_for_stage4_resolution')
        boundary = load_module('stage4_tools/prepare_stage4_boundary_scope.py', 'boundary_for_resolution')
        resolution = load_module('stage4_tools/prepare_stage4_match_resolution.py', 'stage4_match_resolution')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        return resolution.harden(boundary.harden(event.harden(stage2.prepare_text(source))))

    def test_stage4_finishes_fresh_bootstrap_by_stock_state_not_save_marker_alone(self):
        prepared = self.composed_gate()
        self.assertIn('for bootstrap_step in $(seq 1 30)', prepared)
        self.assertIn('bootstrap_state="$(latest_state)"', prepared)
        self.assertIn('dilemma|splashmessage)', prepared)
        self.assertIn('message|startransition)', prepared)
        self.assertIn('webpage)', prepared)
        self.assertIn("capture_log 'fresh Career durable SAVE CAREER confirmed -> GameMenu'", prepared)
        self.assertIn('Fresh Career did not finish stock bootstrap to GameMenu', prepared)
        self.assertNotIn('start_game bootstrap-restart', prepared)
        self.assertNotIn('open_slot0 bootstrap-restart', prepared)
        self.assertNotIn('load_existing bootstrap-restart', prepared)

    def test_fresh_webpagenews_uses_stock_webpage_footer_ok(self):
        prepared = self.composed_gate()
        start = prepared.index('for bootstrap_step in $(seq 1 30)')
        end = prepared.index('[ "$bootstrap_saved" -eq 1 ]', start)
        bootstrap = prepared[start:end]
        webpage = bootstrap.index('webpage)')
        footer = bootstrap.index('press_footer_ok 2', webpage)
        next_case = bootstrap.index('contract)', webpage)
        self.assertLess(webpage, footer)
        self.assertLess(footer, next_case)
        self.assertNotIn('message|webpage|startransition)', bootstrap)

    def test_stage4_removes_redundant_preseason_restart_and_resizes_after_baseline(self):
        prepared = self.composed_gate()
        save_proof = prepared.index("capture_log 'fresh Career durable SAVE CAREER confirmed -> GameMenu'")
        baseline = prepared.index('dump_save natural-baseline; checkpoint natural-baseline')
        resize = prepared.index('adb shell wm size 540x1140')
        season_start = prepared.index('START_EPOCH="$(date +%s)"; SEASON_SEEN=0; CYCLES=0')
        self.assertLess(save_proof, baseline)
        self.assertLess(baseline, resize)
        self.assertLess(resize, season_start)
        self.assertNotIn('start_game natural-lowres', prepared)
        self.assertNotIn('open_slot0 natural-lowres', prepared)
        self.assertNotIn('load_existing natural-lowres', prepared)
        self.assertIn('stage4_tools/validate_frame_png.py "$WORK/natural-lowres-ready.png"', prepared)
        self.assertIn("capture_log 'natural runtime in-process render surface -> 540x1140'", prepared)
        self.assertEqual(1, prepared.count('adb shell wm size 540x1140'))
        self.assertEqual(2, prepared.count('BASE_FLOW_BYTES="$(wc -c < "$FLOW")"'))
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_effective_wm_size_parser_is_rewritten_in_composed_gate(self):
        prepared = self.composed_gate()
        self.assertGreaterEqual(prepared.count("adb shell wm size 2>/dev/null | tr -d '\\r' | tail -1"), 2)
        self.assertNotIn("size=\"$(adb shell wm size 2>/dev/null | tr -d '\\r')\"", prepared)

    def test_kick_detector_scales_large_ball_window_for_half_resolution(self):
        text = Path('stage4_tools/find_kick_ball.py').read_text(encoding='utf-8')
        self.assertIn('win = max(90, min(320, w // 4))', text)
        self.assertIn('stride = max(6, w // 54)', text)


if __name__ == '__main__':
    unittest.main()
