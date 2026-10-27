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


class Stage4BoundaryScopeTests(unittest.TestCase):
    def test_only_post_baseline_newseason_markers_count(self):
        module = load_module('stage4_tools/prepare_stage4_boundary_scope.py', 'stage4_boundary_scope')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('BASE_FLOW_BYTES="$(wc -c < "$FLOW")"', prepared)
        self.assertIn('post-baseline-season-flow.log', prepared)
        self.assertIn('tail -c +$((BASE_FLOW_BYTES + 1)) "$FLOW"', prepared)
        marker_check = prepared.index("grep -q 'CallFunc:[[:space:]]*NewSeasonSetUp1' \"$WORK/post-baseline-season-flow.log\"")
        baseline = prepared.index('BASE_FLOW_BYTES=')
        self.assertLess(baseline, marker_check)
        # This scope hardening must not create any direct season/match shortcut.
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_completed_rollover_short_circuits_navigation_before_post_rollover_play(self):
        module = load_module('stage4_tools/prepare_stage4_boundary_scope.py', 'stage4_boundary_stop')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        self.assertIn('stage4_live_boundary_seen(){', prepared)
        self.assertIn('STAGE4_BOUNDARY_REACHED=1', prepared)
        self.assertIn('natural season boundary complete; stop before post-rollover Play', prepared)
        self.assertIn('[ "${STAGE4_BOUNDARY_REACHED:-0}" -eq 1 ] && return 0', prepared)

        nav_capture = prepared.index('capture_log "navigate step $step -> $state"')
        boundary_probe = prepared.index('if stage4_live_boundary_seen; then', nav_capture)
        ordinary_match_return = prepared.index('[ "$state" = match ] && return 0', nav_capture)
        self.assertLess(boundary_probe, ordinary_match_return)

        cycle_nav = prepared.index('navigate_until_match || { shot "cycle-$cycle-no-match"; return 1; }')
        cycle_boundary_return = prepared.index('[ "${STAGE4_BOUNDARY_REACHED:-0}" -eq 1 ] && return 0', cycle_nav)
        cycle_match_shot = prepared.index('shot "cycle-$cycle-match"', cycle_nav)
        self.assertLess(cycle_boundary_return, cycle_match_shot)

        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)


if __name__ == '__main__':
    unittest.main()
