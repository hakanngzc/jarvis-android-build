import unittest

from patch_lifecycle_probe_v4 import CENTER_ANCHOR, harden_generated_script


class LifecyclePatchV4Test(unittest.TestCase):
    def test_uses_ui_hierarchy_instead_of_center_guess(self):
        out = harden_generated_script('before\n' + CENTER_ANCHOR + '\nafter\n')
        self.assertIn('uiautomator dump /sdcard/nss-recents.xml', out)
        self.assertIn("terms=('new star soccer','newstarsoccer')", out)
        self.assertIn('recents_target_found', out)
        self.assertNotIn('x=$((w/2))', out)

    def test_keeps_missing_target_fail_closed(self):
        out = harden_generated_script(CENTER_ANCHOR)
        self.assertIn('NSS task target not found in Recents', out)
        self.assertIn('"${tag}_recents_target_found" FAIL', out)

    def test_refuses_changed_v3_shape(self):
        with self.assertRaises(ValueError):
            harden_generated_script('no center anchor')


if __name__ == '__main__':
    unittest.main()
