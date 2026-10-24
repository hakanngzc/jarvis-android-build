import unittest

from patch_lifecycle_probe_v9 import CONTEXT_SURVIVAL_DRIVER_REPLACEMENT
from patch_lifecycle_probe_v10 import CONTEXT_SURVIVAL_RENDER_DRIVER_REPLACEMENT, replace_v9_candidate


class LifecyclePatchV10Test(unittest.TestCase):
    def test_replaces_v9_black_screen_candidate_with_render_reenable_candidate(self):
        generated = replace_v9_candidate(CONTEXT_SURVIVAL_DRIVER_REPLACEMENT)
        self.assertEqual(generated, CONTEXT_SURVIVAL_RENDER_DRIVER_REPLACEMENT)
        self.assertIn('patch_gl_context_survival_render.py', generated)
        self.assertIn('VERDICT=LIFECYCLE_GL_CONTEXT_SURVIVAL_RENDER_PATCH_APPLIED', generated)
        self.assertNotIn('patch_gl_context_survival.py', generated)

    def test_refuses_driver_without_exact_v9_candidate(self):
        with self.assertRaises(ValueError):
            replace_v9_candidate('candidate shape changed')


if __name__ == '__main__':
    unittest.main()
