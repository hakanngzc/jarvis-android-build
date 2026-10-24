import unittest

from patch_gl_resume_race import build_focus_sequences, rewrite_focus_units


class GLResumeRacePatchTest(unittest.TestCase):
    def setUp(self):
        self.ids = dict(
            view_field_id=0x155C,
            view_resume_method_id=0x4A37,
            game_field_id=0x155B,
            game_resume_method_id=0x4A7B,
            game_suspend_method_id=0x4A85,
            view_pause_method_id=0x4A36,
        )

    def test_focus_gain_resumes_game_before_restarting_gl_thread(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(stock[2:7], [0x0154, 0x155C, 0x106E, 0x4A37, 0x0001])
        self.assertEqual(patched[2:7], [0x0154, 0x155B, 0x106E, 0x4A7B, 0x0001])
        self.assertEqual(patched[7:12], [0x0154, 0x155C, 0x106E, 0x4A37, 0x0001])

    def test_focus_loss_order_is_unchanged(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(stock[13:], patched[13:])
        self.assertEqual(patched[13:18], [0x0154, 0x155B, 0x106E, 0x4A85, 0x0001])
        self.assertEqual(patched[18:23], [0x0154, 0x155C, 0x106E, 0x4A36, 0x0001])

    def test_rewrite_refuses_any_non_stock_body(self):
        stock, _ = build_focus_sequences(**self.ids)
        changed = list(stock)
        changed[4] ^= 1
        with self.assertRaises(ValueError):
            rewrite_focus_units(changed, **self.ids)

    def test_rewrite_changes_only_focus_gain_call_order(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(rewrite_focus_units(stock, **self.ids), patched)
        diffs = [i for i, (a, b) in enumerate(zip(stock, patched)) if a != b]
        self.assertEqual(diffs, [3, 5, 8, 10])


if __name__ == '__main__':
    unittest.main()
