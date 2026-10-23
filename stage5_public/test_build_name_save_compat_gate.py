#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'stage5_public'))

from build_name_save_compat_gate import inject_stage5


class Stage5GateBuilderTests(unittest.TestCase):
    def test_injects_after_real_slot0_save_and_stops_before_slot1(self):
        source = 'create_career 0 slot0-seed\ncreate_career 1 slot1\nmanual_load_slot 1 slot1-restart\n'
        out = inject_stage5(source)
        self.assertEqual(out.count('create_career 0 slot0-seed'), 1)
        self.assertEqual(out.count('create_career 1 slot1'), 1)
        self.assertIn('STAGE5_PATCH_ID_CONTRACT', out)
        self.assertIn('STAGE5_SAVE_UNCHANGED_AFTER_UPDATE', out)
        self.assertIn('STAGE5_PATCHED_TABLE_INSTALLED', out)
        self.assertIn('STAGE5_OLD_SAVE_LOAD', out)
        self.assertIn('STAGE5_NAME_SAVE_COMPAT', out)
        self.assertLess(out.index('create_career 0 slot0-seed'), out.index('STAGE5_PATCH_ID_CONTRACT'))
        self.assertLess(out.index("echo 'VERDICT=STAGE5_PUBLIC_NAME_SAVE_COMPAT_PASS'"), out.index('create_career 1 slot1'))
        self.assertIn("exit 0\n\ncreate_career 1 slot1", out)

    def test_rejects_missing_or_duplicate_anchor(self):
        with self.assertRaisesRegex(ValueError, 'anchor'):
            inject_stage5('echo nope\n')
        duplicated = 'create_career 0 slot0-seed\ncreate_career 1 slot1\n' * 2
        with self.assertRaisesRegex(ValueError, 'anchor'):
            inject_stage5(duplicated)


if __name__ == '__main__':
    unittest.main()
