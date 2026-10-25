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


if __name__ == '__main__':
    unittest.main()
