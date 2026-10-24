import unittest

from patch_lifecycle_probe_v4 import (
    CENTER_ANCHOR,
    FATAL_ANCHOR,
    GL_DRIVER_ANCHOR,
    CAREER_ROUNDTRIP_ANCHOR,
    harden_fatal_check,
    harden_generated_script,
    inject_gl_context_survival_patch,
    inject_stress_roundtrips,
)


PLAY_EDGE_ANCHOR = 'press_play(){ local x y; read -r x y < <(logical_xy 553 829); press_physical "$x" "$y" "${1:-2}"; }'


class LifecyclePatchV4Test(unittest.TestCase):
    def test_uses_ui_hierarchy_instead_of_center_guess(self):
        out = harden_generated_script('before\n' + CENTER_ANCHOR + '\nafter\n')
        self.assertIn('uiautomator dump /sdcard/nss-recents.xml', out)
        self.assertIn("terms=('new star soccer','newstarsoccer')", out)
        self.assertIn('recents_target_found', out)
        self.assertNotIn('x=$((w/2))', out)

    def test_accepts_only_one_unlabeled_structural_task_card(self):
        out = harden_generated_script(CENTER_ANCHOR)
        self.assertIn("endswith('/overview_panel')", out)
        self.assertIn("endswith('/snapshot')", out)
        self.assertIn("if len(cards)==1", out)
        self.assertIn('multiple unlabeled Recents task cards', out)
        self.assertIn('unique-structural-task-card', out)

    def test_keeps_missing_or_ambiguous_target_fail_closed(self):
        out = harden_generated_script(CENTER_ANCHOR)
        self.assertIn('NSS task target not found unambiguously in Recents', out)
        self.assertIn('"${tag}_recents_target_found" FAIL', out)

    def test_retries_verified_recents_target_at_most_three_times(self):
        out = harden_generated_script(CENTER_ANCHOR)
        self.assertIn('for recents_attempt in 1 2 3; do', out)
        self.assertIn('input tap "$x" "$y"', out)
        self.assertIn('lifecycle-${tag}-recents-attempt-${recents_attempt}.txt', out)
        self.assertIn('NSS foregrounded from verified Recents target on attempt', out)
        self.assertNotIn('while true', out)

    def test_moves_play_tap_from_edge_to_verified_button_center(self):
        out = harden_generated_script(CENTER_ANCHOR + '\n' + PLAY_EDGE_ANCHOR)
        self.assertIn('logical_xy 553 900', out)
        self.assertNotIn('logical_xy 553 829', out)

    def test_measurement_service_anr_is_the_only_ignored_anr(self):
        out = harden_fatal_check(FATAL_ANCHOR)
        self.assertIn('AppMeasurementService', out)
        self.assertIn('runtime-ignored-appmeasurement-anr.txt', out)
        self.assertIn('[ "$anr_count" -eq "$measurement_count" ]', out)
        self.assertIn('FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer', out)
        self.assertIn('Process: com\\.newstargames\\.newstarsoccer, PID:', out)

    def test_measurement_filter_still_fails_unknown_nss_anr(self):
        out = harden_fatal_check(FATAL_ANCHOR)
        self.assertIn('[ "$anr_count" -gt 0 ]', out)
        self.assertIn("echo 'NSS-owned crash/ANR detected'", out)
        self.assertIn('return 1', out)

    def test_fatal_filter_refuses_changed_source_shape(self):
        with self.assertRaises(ValueError):
            harden_fatal_check('fatal_check(){ echo changed; }')

    def test_injects_candidate_gl_context_survival_patch_after_startup_harness(self):
        out = inject_gl_context_survival_patch(GL_DRIVER_ANCHOR)
        self.assertIn('base-career-probe-pre-gl.apk', out)
        self.assertIn('lifecycle/patch_gl_context_survival.py', out)
        self.assertIn('LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH.json', out)
        self.assertNotIn('patch_gl_resume_race.py', out)
        self.assertNotIn('LIFECYCLE_GL_RESUME_PATCH.json', out)

    def test_stresses_real_recents_roundtrip_five_times(self):
        out = inject_stress_roundtrips(CAREER_ROUNDTRIP_ANCHOR)
        self.assertIn('for lifecycle_cycle in 1 2 3 4 5', out)
        self.assertIn('lifecycle_background_roundtrip "career-${lifecycle_cycle}"', out)
        self.assertNotIn('\nlifecycle_background_roundtrip career\n', '\n' + out + '\n')

    def test_refuses_changed_v3_shape(self):
        with self.assertRaises(ValueError):
            harden_generated_script('no center anchor')


if __name__ == '__main__':
    unittest.main()
