import unittest
from pathlib import Path

from patch_lifecycle_probe_v5 import ACTIVITY_ONSTOP_REPLACEMENT
from patch_lifecycle_probe_v6 import (
    COMBINED_DRIVER_REPLACEMENT,
    combine_activity_and_resume,
)


class LifecyclePatchV6Test(unittest.TestCase):
    def test_combines_activity_super_fix_then_resume_order_on_intermediate_apk(self):
        sample = 'before\n' + ACTIVITY_ONSTOP_REPLACEMENT + '\nafter\n'
        out = combine_activity_and_resume(sample)
        self.assertIn('patch_activity_super_lifecycle.py', out)
        self.assertIn('base-career-probe-super.apk', out)
        self.assertIn('LIFECYCLE_ACTIVITY_SUPER_PATCH_APPLIED', out)
        self.assertIn('patch_gl_resume_race.py', out)
        self.assertIn('LIFECYCLE_GL_RESUME_PATCH_APPLIED', out)
        self.assertIn('LIFECYCLE_GL_RESUME_PATCH.json', out)
        self.assertIn('LIFECYCLE_GL_RESUME_PATCH.txt', out)
        self.assertIn('base-career-probe.apk', out)
        self.assertLess(out.index('patch_activity_super_lifecycle.py'), out.index('patch_gl_resume_race.py'))

    def test_combined_driver_keeps_graphics_dump_and_both_evidence_gates(self):
        self.assertIn('dump_graphics_lifecycle_code.py', COMBINED_DRIVER_REPLACEMENT)
        self.assertIn('LIFECYCLE_GRAPHICS_CODE.json', COMBINED_DRIVER_REPLACEMENT)
        self.assertIn('LIFECYCLE_ACTIVITY_SUPER_PATCH.json', COMBINED_DRIVER_REPLACEMENT)
        self.assertIn('LIFECYCLE_GL_RESUME_PATCH.json', COMBINED_DRIVER_REPLACEMENT)
        self.assertIn("grep -q 'VERDICT=LIFECYCLE_ACTIVITY_SUPER_PATCH_APPLIED'", COMBINED_DRIVER_REPLACEMENT)
        self.assertIn("grep -q 'VERDICT=LIFECYCLE_GL_RESUME_PATCH_APPLIED'", COMBINED_DRIVER_REPLACEMENT)

    def test_refuses_changed_v5_driver_shape(self):
        with self.assertRaises(ValueError):
            combine_activity_and_resume('no activity candidate here')

    def test_patch_script_builds_on_v5_then_combines_candidate(self):
        src = Path('patch_lifecycle_probe_v6.py').read_text(encoding='utf-8')
        body = src.split('def patch_script(text: str) -> str:', 1)[1].split('def main()', 1)[0]
        self.assertIn('v5_patch_script(text)', body)
        self.assertIn('combine_activity_and_resume(generated)', body)


if __name__ == '__main__':
    unittest.main()
