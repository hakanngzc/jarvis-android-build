import unittest

from patch_lifecycle_probe_v6 import COMBINED_DRIVER_REPLACEMENT
from patch_lifecycle_probe_v9 import CONTEXT_SURVIVAL_DRIVER_REPLACEMENT, replace_failed_gl_candidate


class LifecyclePatchV9Test(unittest.TestCase):
    def test_replaces_failed_combined_super_resume_candidate_with_context_survival(self):
        generated = replace_failed_gl_candidate(COMBINED_DRIVER_REPLACEMENT)
        self.assertEqual(generated, CONTEXT_SURVIVAL_DRIVER_REPLACEMENT)
        self.assertIn('patch_gl_context_survival.py', generated)
        self.assertIn('VERDICT=LIFECYCLE_GL_CONTEXT_SURVIVAL_PATCH_APPLIED', generated)
        self.assertNotIn('patch_gl_resume_race.py', generated)
        self.assertNotIn('patch_activity_super_lifecycle.py', generated)

    def test_refuses_driver_without_exact_failed_candidate(self):
        with self.assertRaises(ValueError):
            replace_failed_gl_candidate('candidate shape changed')


if __name__ == '__main__':
    unittest.main()
