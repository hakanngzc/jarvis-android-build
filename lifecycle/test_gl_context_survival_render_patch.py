import unittest

from patch_gl_context_survival_render import build_focus_sequences, rewrite_focus_units


class GLContextSurvivalRenderPatchTest(unittest.TestCase):
    def setUp(self):
        self.ids = dict(
            view_field_id=0x155C,
            view_resume_method_id=0x4A37,
            game_field_id=0x155B,
            game_resume_method_id=0x4A7B,
            game_suspend_method_id=0x4A85,
            view_pause_method_id=0x4A36,
            can_render_field_id=0x1579,
        )

    def test_focus_gain_resumes_game_and_reenables_render_without_view_resume(self):
        stock, patched = build_focus_sequences(**self.ids)
        # Gain-focus block is exactly 10 code units, preserving the branch target.
        gain = patched[2:12]
        self.assertEqual(gain[0:2], [0x0154, self.ids['game_field_id']])
        self.assertEqual(gain[2:5], [0x106E, self.ids['game_resume_method_id'], 0x0001])
        self.assertEqual(gain[5], 0x1012)  # const/4 v0, #1
        self.assertEqual(gain[6:8], [0x015B, self.ids['can_render_field_id']])  # iput-boolean v0, v1
        self.assertEqual(gain[8:10], [0x0000, 0x0000])
        self.assertNotIn(self.ids['view_resume_method_id'], gain)

    def test_focus_loss_keeps_suspend_and_removes_view_pause(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(patched[13:18], stock[13:18])
        self.assertEqual(patched[18:23], [0, 0, 0, 0, 0])

    def test_control_flow_shape_is_unchanged(self):
        stock, patched = build_focus_sequences(**self.ids)
        self.assertEqual(len(patched), len(stock))
        self.assertEqual(patched[0:2], stock[0:2])
        self.assertEqual(patched[12], stock[12])
        self.assertEqual(patched[23], stock[23])

    def test_rewrite_refuses_non_stock_body(self):
        stock, _ = build_focus_sequences(**self.ids)
        changed = list(stock)
        changed[9] ^= 1
        with self.assertRaises(ValueError):
            rewrite_focus_units(changed, **self.ids)


if __name__ == '__main__':
    unittest.main()
