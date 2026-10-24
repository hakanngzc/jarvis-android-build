import unittest

from patch_lifecycle_probe_v4 import CENTER_ANCHOR, harden_generated_script


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

    def test_refuses_changed_v3_shape(self):
        with self.assertRaises(ValueError):
            harden_generated_script('no center anchor')


if __name__ == '__main__':
    unittest.main()
