import unittest

from patch_lifecycle_probe_v4 import GL_DRIVER_REPLACEMENT
from patch_lifecycle_probe_v5 import ACTIVITY_ONSTOP_REPLACEMENT, replace_resume_candidate


class LifecyclePatchV5Test(unittest.TestCase):
    def test_replaces_failed_resume_order_candidate_with_activity_onstop_only(self):
        sample='before\n'+GL_DRIVER_REPLACEMENT+'\nafter\n'
        out=replace_resume_candidate(sample)
        self.assertIn('patch_activity_super_lifecycle.py',out)
        self.assertIn('LIFECYCLE_ACTIVITY_ONSTOP_PATCH.json',out)
        self.assertIn('base-career-probe-stock.apk',out)
        self.assertIn('base-career-probe.apk',out)
        self.assertNotIn('patch_gl_resume_race.py',out)
        self.assertNotIn('patch_gl_context_survival.py',out)
        self.assertNotIn('patch_preserve_egl_activity.py',out)

    def test_candidate_is_exact_replacement_block(self):
        self.assertIn('patch_activity_super_lifecycle.py',ACTIVITY_ONSTOP_REPLACEMENT)
        self.assertIn('VERDICT',ACTIVITY_ONSTOP_REPLACEMENT)

    def test_refuses_changed_v4_candidate_shape(self):
        with self.assertRaises(ValueError):
            replace_resume_candidate('no resume candidate here')


if __name__=='__main__':
    unittest.main()
