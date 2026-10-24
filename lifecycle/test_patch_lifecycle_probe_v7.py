import unittest
from pathlib import Path

from patch_lifecycle_probe_v7 import RELOAD_HELPER_REPLACEMENT, harden_reload_navigation


class LifecyclePatchV7Test(unittest.TestCase):
    def test_reload_uses_visual_slot_fingerprint_and_bounded_retry(self):
        body = RELOAD_HELPER_REPLACEMENT
        self.assertIn('for attempt in 1 2 3; do', body)
        self.assertIn('find_slot0_target', body)
        self.assertIn('lifecycle-reload-slot-attempt-${attempt}.png', body)
        self.assertIn("LoadCareer saveslot:[[:space:]]*0", body)
        self.assertIn('loaded=1', body)
        self.assertNotIn('while true', body)

    def test_missing_slot_fingerprint_allows_one_back_then_requires_fingerprint(self):
        body = RELOAD_HELPER_REPLACEMENT
        self.assertEqual(body.count('adb shell input keyevent 4'), 1)
        self.assertIn('lifecycle-reload-slot-attempt-${attempt}-post-back.png', body)
        self.assertIn('reload SaveSlot fingerprint still missing after one BACK', body)
        self.assertIn('return 1', body)

    def test_failed_attempt_captures_diagnostics(self):
        body = RELOAD_HELPER_REPLACEMENT
        self.assertIn('dumpsys activity activities', body)
        self.assertIn('dumpsys window windows', body)
        self.assertIn('uiautomator dump', body)
        self.assertIn('logcat -d -v threadtime', body)
        self.assertIn('lifecycle-reload-slot-attempt-${attempt}-miss', body)

    def test_patch_script_builds_on_v6(self):
        src = Path('patch_lifecycle_probe_v7.py').read_text(encoding='utf-8')
        patch_body = src.split('def patch_script(text: str) -> str:', 1)[1].split('def main()', 1)[0]
        self.assertIn('v6_patch_script(text)', patch_body)
        self.assertIn('harden_reload_navigation(generated)', patch_body)

    def test_refuses_changed_v6_reload_shape(self):
        with self.assertRaises(ValueError):
            harden_reload_navigation('reload helper shape changed')


if __name__ == '__main__':
    unittest.main()
