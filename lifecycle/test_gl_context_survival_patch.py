import unittest

from patch_gl_context_survival import build_focus_sequences, rewrite_focus_units


class GLContextSurvivalPatchTest(unittest.TestCase):
    def setUp(self):
        self.ids = dict(
            view_field_id=0x155C,
            view_resume_method_id=0x4A37,
            game_field_id=0x155B,
            game_resume_method_id=0x4A7B,
            game_suspend_method_id=0x4A85,
            view_pause_method_id=0x4A36,
        )

    def test_keeps_game_suspend_resume_but_removes_glsurfaceview_pause_resume(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(patched[2:7], [0, 0, 0, 0, 0])
        self.assertEqual(patched[7:12], stock[7:12])
        self.assertEqual(patched[13:18], stock[13:18])
        self.assertEqual(patched[18:23], [0, 0, 0, 0, 0])

    def test_control_flow_offsets_and_return_are_unchanged(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(patched[0:2], stock[0:2])
        self.assertEqual(patched[12], stock[12])
        self.assertEqual(patched[23], stock[23])

    def test_rewrite_refuses_any_non_stock_body(self):
        stock, _ = build_focus_sequences(**self.ids)
        changed = list(stock)
        changed[10] ^= 1
        with self.assertRaises(ValueError):
            rewrite_focus_units(changed, **self.ids)

    def test_rewrite_changes_only_the_two_glsurfaceview_call_blocks(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(rewrite_focus_units(stock, **self.ids), patched)
        diffs = [i for i, (a, b) in enumerate(zip(stock, patched)) if a != b]
        self.assertEqual(diffs, [2, 3, 4, 5, 6, 18, 19, 20, 21, 22])


if __name__ == '__main__':
    unittest.main()
