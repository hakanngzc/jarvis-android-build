import unittest

from patch_long_career_driver import (
    PATCH_ANCHOR,
    TAIL_MARKER,
    SIGN_ANCHOR,
    CAREER_OPEN_ANCHOR,
    SLOT_ANCHOR,
    POST_CREATE_ANCHOR,
    PLAY_EDGE_ANCHOR,
    FATAL_ANCHOR,
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
            PLAY_EDGE_ANCHOR + '\n' +
            'sign_one(){\n' + SIGN_ANCHOR + '\n}\n' +
            FATAL_ANCHOR + '\n' +
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

    def test_save_capture_prepares_root_access_before_baseline(self):
        out = transform(self.fixture())
        self.assertIn('prepare_save_access(){', out)
        self.assertIn('adb root > "$OUT/endurance-adb-root.txt"', out)
        self.assertIn('adb wait-for-device', out)
        self.assertLess(out.index('prepare_save_access\n'), out.index('dump_save season-0-baseline'))

    def test_uses_verified_api29_play_hitbox_center(self):
        out = transform(self.fixture())
        self.assertIn('logical_xy 553 900', out)
        self.assertNotIn('logical_xy 553 829', out)

    def test_initial_navigation_uses_verified_mainmenu_center(self):
        out = transform(self.fixture())
        self.assertIn('logical_xy 480 624', out)
        self.assertNotIn('logical_xy 480 664', out)
        self.assertIn('logical_xy 320 280', out)
        self.assertNotIn('press_physical 810 1450 2', out)
        self.assertNotIn('find_slot0_target "$OUT/saveslot.png"', out)

    def test_crosses_real_save_boundary_before_endurance_loop(self):
        out = transform(self.fixture())
        self.assertIn('Initial Career did not reach save boundary', out)
        self.assertIn('LoadCareer saveslot:', out)
        self.assertIn('endurance-reloaded-gamemenu', out)
        self.assertIn('for reopen_attempt in 1 2 3', out)
        self.assertIn('endurance-reload-saveslot-attempt-${reopen_attempt}', out)
        self.assertIn('Could not reopen SaveSlot after initial Career save', out)
        self.assertNotIn(POST_CREATE_ANCHOR, out)

    def test_season_entry_retries_only_until_leaguefixtures_is_verified(self):
        out = transform(self.fixture())
        self.assertIn('enter_leaguefixtures(){', out)
        self.assertIn('for attempt in 1 2 3', out)
        self.assertIn('press_play 3', out)
        self.assertIn('season-${season}-leaguefixtures-attempt-${attempt}', out)
        self.assertIn('enter_leaguefixtures "$season"', out)
        self.assertNotIn('press_play 3\n  wait_log \'Create Screen:[[:space:]]*leaguefixtures', out)

    def test_season_entry_captures_state_focus_and_ui_before_each_tap(self):
        out = transform(self.fixture())
        self.assertIn('capture_season_entry_diagnostics(){', out)
        self.assertIn('shot "season-${season}-leaguefixtures-attempt-${attempt}-before"', out)
        self.assertIn('dumpsys activity activities', out)
        self.assertIn('dumpsys window windows', out)
        self.assertIn('uiautomator dump /sdcard/endurance-entry.xml', out)
        self.assertIn('${prefix}-ui.xml', out)
        capture_at = out.index('capture_season_entry_diagnostics "$season" "$attempt"')
        tap_at = out.index('press_play 3', capture_at)
        self.assertLess(capture_at, tap_at)

    def test_requires_restart_reload_after_every_season(self):
        out = transform(self.fixture())
        self.assertIn('for season in $(seq 1 "$SEASON_COUNT")', out)
        self.assertIn('restart_saved_career "season-${season}-reload"', out)
        self.assertIn('dump_save "season-${season}-reload"', out)
        self.assertIn('fatal_check', out)

    def test_restart_reload_waits_for_stock_auto_loadcareer(self):
        out = transform(self.fixture())
        self.assertIn('restart_saved_career(){', out)
        self.assertIn('adb shell am force-stop "$PKG"', out)
        self.assertIn('adb shell am start -n "$PKG/.MonkeyGame"', out)
        self.assertIn("wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 \"$tag-loadcareer\"", out)
        self.assertIn("wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 \"$tag-gamemenu\"", out)

    def test_restart_reload_requires_stable_last_active_gamemenu(self):
        out = transform(self.fixture())
        self.assertIn('last_active_screen(){', out)
        self.assertIn("grep -Ei 'SETTING ACTIVE:|SetActive:'", out)
        self.assertIn('tail -1', out)
        self.assertIn('local stable=0', out)
        self.assertIn('if [ "$screen" = gamemenu ]', out)
        self.assertIn('stable=$((stable+1))', out)
        self.assertIn('[ "$stable" -ge 2 ]', out)
        self.assertIn('settle_loaded_gamemenu "$tag"', out)

    def test_measurement_service_anr_is_the_only_ignored_anr(self):
        out = transform(self.fixture())
        self.assertIn('local anr_count measurement_count', out)
        self.assertIn("anr_count=\"$(grep -cE 'ANR in com\\.newstargames\\.newstarsoccer'", out)
        self.assertIn('Reason: executing service com\\.newstargames\\.newstarsoccer/com\\.google\\.android\\.gms\\.measurement\\.AppMeasurementService', out)
        self.assertIn('[ "$anr_count" -eq "$measurement_count" ]', out)
        self.assertIn('runtime-ignored-appmeasurement-anr.txt', out)
        self.assertIn("grep -qE 'Process: com\\.newstargames\\.newstarsoccer, PID:|FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer'", out)
        self.assertIn("echo 'NSS-owned crash/ANR detected'", out)

    def test_final_flow_gate_uses_same_narrow_measurement_rule(self):
        out = transform(self.fixture())
        self.assertIn('flow_fatal_check(){', out)
        self.assertIn('flow_anr_count', out)
        self.assertIn('flow_measurement_count', out)
        self.assertIn('[ "$flow_anr_count" -eq "$flow_measurement_count" ]', out)
        self.assertIn('flow_fatal_check', out)
        self.assertNotIn("! grep -qiE 'ANR in com\\.newstargames\\.newstarsoccer|Process: com\\.newstargames\\.newstarsoccer, PID:|FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer' \"$FLOW\"", out)

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
