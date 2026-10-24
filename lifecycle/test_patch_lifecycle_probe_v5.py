import unittest
from pathlib import Path

from patch_lifecycle_probe_v4 import GL_DRIVER_REPLACEMENT
from patch_lifecycle_probe_v5 import (
    ACTIVITY_ONSTOP_REPLACEMENT,
    CHOOSECLUB_WAIT_ANCHOR,
    inject_chooseclub_timeout_diagnostics,
    replace_resume_candidate,
)


class LifecyclePatchV5Test(unittest.TestCase):
    def test_replaces_failed_resume_order_candidate_with_activity_onstop_only(self):
        sample='before\n'+GL_DRIVER_REPLACEMENT+'\nafter\n'
        out=replace_resume_candidate(sample)
        self.assertIn('dump_graphics_lifecycle_code.py',out)
        self.assertIn('LIFECYCLE_GRAPHICS_CODE.json',out)
        self.assertIn('LIFECYCLE_GRAPHICS_CODE.txt',out)
        self.assertIn('patch_activity_super_lifecycle.py',out)
        self.assertIn('LIFECYCLE_ACTIVITY_ONSTOP_PATCH.json',out)
        self.assertIn('base-career-probe-stock.apk',out)
        self.assertIn('base-career-probe.apk',out)
        self.assertNotIn('patch_gl_resume_race.py',out)
        self.assertNotIn('patch_gl_context_survival.py',out)
        self.assertNotIn('patch_preserve_egl_activity.py',out)

    def test_candidate_is_exact_replacement_block(self):
        self.assertIn('dump_graphics_lifecycle_code.py',ACTIVITY_ONSTOP_REPLACEMENT)
        self.assertIn('LIFECYCLE_GRAPHICS_CODE.json',ACTIVITY_ONSTOP_REPLACEMENT)
        self.assertIn('patch_activity_super_lifecycle.py',ACTIVITY_ONSTOP_REPLACEMENT)
        self.assertIn('VERDICT',ACTIVITY_ONSTOP_REPLACEMENT)

    def test_refuses_changed_v4_candidate_shape(self):
        with self.assertRaises(ValueError):
            replace_resume_candidate('no resume candidate here')

    def test_chooseclub_timeout_captures_focus_ui_screenshot_and_logcat_without_recovery_tap(self):
        out = inject_chooseclub_timeout_diagnostics('before\n' + CHOOSECLUB_WAIT_ANCHOR + '\nafter\n')
        self.assertIn('if ! wait_log', out)
        self.assertIn('shot lifecycle-chooseclub-timeout', out)
        self.assertIn('dumpsys activity activities', out)
        self.assertIn('lifecycle-chooseclub-timeout-activity.txt', out)
        self.assertIn('dumpsys window windows', out)
        self.assertIn('lifecycle-chooseclub-timeout-window.txt', out)
        self.assertIn('uiautomator dump /sdcard/lifecycle-chooseclub-timeout.xml', out)
        self.assertIn('lifecycle-chooseclub-timeout-ui.xml', out)
        self.assertIn('lifecycle-chooseclub-timeout.log', out)
        self.assertIn('exit 204', out)
        self.assertNotIn('input keyevent 4', out)
        self.assertNotIn('input tap', out)

    def test_patch_script_applies_chooseclub_timeout_diagnostics(self):
        src = Path('patch_lifecycle_probe_v5.py').read_text(encoding='utf-8')
        body = src.split('def patch_script(text: str) -> str:', 1)[1].split('def main()', 1)[0]
        self.assertIn('inject_chooseclub_timeout_diagnostics(generated)', body)

    def test_chooseclub_diagnostics_refuses_changed_source_shape(self):
        with self.assertRaises(ValueError):
            inject_chooseclub_timeout_diagnostics('no chooseclub wait anchor')


if __name__=='__main__':
    unittest.main()
