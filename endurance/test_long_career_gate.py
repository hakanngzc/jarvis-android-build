import unittest

from patch_long_career_driver import (
    PATCH_ANCHOR,
    TAIL_MARKER,
    SIGN_ANCHOR,
    CAREER_OPEN_ANCHOR,
    SLOT_ANCHOR,
    POST_CREATE_ANCHOR,
    transform,
)
from patch_long_career_season_probe import SEASON_DELTA, build_probe_units


class ProgressiveSeasonProbeTest(unittest.TestCase):
    def test_probe_reads_current_date_before_adding_full_season(self):
        units = build_probe_units(10, 11, 12, 13, 14)
        self.assertEqual(units[:6], [0x0062, 10, 0x0254, 11, 0x2352, 12])
        self.assertIn(0x33D0, units)
        add_at = units.index(0x33D0)
        self.assertEqual(units[add_at + 1], SEASON_DELTA)
        self.assertEqual(SEASON_DELTA, 365)

    def test_probe_calls_real_newseason_after_sentinel(self):
        units = build_probe_units(10, 11, 12, 13, 14)
        self.assertIn(0x7112, units)
        self.assertIn(0x206E, units)
        call_at = units.index(0x206E)
        self.assertEqual(units[call_at + 1], 14)


class LongCareerDriverTransformTest(unittest.TestCase):
    def fixture(self):
        return (
            'header\n' +
            PATCH_ANCHOR + '\n' +
            'sign_one(){\n' + SIGN_ANCHOR + '\n}\n' +
            CAREER_OPEN_ANCHOR + '\n' +
            SLOT_ANCHOR + '\n' +
            POST_CREATE_ANCHOR + '\n' +
            'pre-tail\n' + TAIL_MARKER + '\nold-stage3-tail\n'
        )

    def test_replaces_match_patch_with_progressive_season_probe(self):
        out = transform(self.fixture())
        self.assertIn('patch_long_career_season_probe.py', out)
        self.assertNotIn('patch_stage3_knockout_apk.py', out)

    def test_repairs_latent_sign_one_nounset_bug(self):
        out = transform(self.fixture())
        self.assertIn('local src="$1" dst="$2"\n  local aligned=', out)
        self.assertNotIn(SIGN_ANCHOR, out)

    def test_dump_save_initializes_tag_before_using_it_under_nounset(self):
        out = transform(self.fixture())
        self.assertIn('local tag="$1"\n  local remote=', out)
        self.assertNotIn('local tag="$1" remote=', out)

    def test_initial_navigation_uses_stable_logical_targets(self):
        out = transform(self.fixture())
        self.assertIn('logical_xy 480 664', out)
        self.assertIn('logical_xy 320 280', out)
        self.assertNotIn('press_physical 810 1450 2', out)
        self.assertNotIn('find_slot0_target "$OUT/saveslot.png"', out)

    def test_crosses_real_save_boundary_before_endurance_loop(self):
        out = transform(self.fixture())
        self.assertIn('Initial Career did not reach save boundary', out)
        self.assertIn('LoadCareer saveslot:', out)
        self.assertIn('endurance-reloaded-gamemenu', out)
        self.assertNotIn(POST_CREATE_ANCHOR, out)

    def test_requires_restart_reload_after_every_season(self):
        out = transform(self.fixture())
        self.assertIn('for season in $(seq 1 "$SEASON_COUNT")', out)
        self.assertIn('open_saved_slot0 "season-${season}-reload"', out)
        self.assertIn('dump_save "season-${season}-reload"', out)
        self.assertIn('fatal_check', out)
        self.assertIn('LoadCareer saveslot:', out)

    def test_default_is_eight_progressive_seasons(self):
        out = transform(self.fixture())
        self.assertIn('SEASON_COUNT="${LONG_CAREER_SEASONS:-8}"', out)
        self.assertIn('verify_long_career.py "$OUT" "$SEASON_COUNT"', out)

    def test_old_stage3_tail_is_removed(self):
        out = transform(self.fixture())
        self.assertNotIn('old-stage3-tail', out)

    def test_refuses_unknown_source_shape(self):
        with self.assertRaises(ValueError):
            transform('header\n' + TAIL_MARKER + '\n')


if __name__ == '__main__':
    unittest.main()
