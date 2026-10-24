import unittest

from patch_lifecycle_probe_v4 import NAV_ANCHOR, harden_match_navigation


class MatchNavigationStateTest(unittest.TestCase):
    def test_dropped_touch_retries_last_known_state_with_bound(self):
        out = harden_match_navigation(NAV_ANCHOR)
        self.assertIn('last_known=gamemenu', out)
        self.assertIn('unknown_retries=0', out)
        self.assertIn('state="$last_known"', out)
        self.assertIn('unknown_retries=$((unknown_retries+1))', out)
        self.assertIn('[ "$unknown_retries" -le 3 ]', out)
        self.assertIn('navigation touch/state retry budget exhausted', out)
        self.assertIn("wait_state 'match message leaguefixtures league gamemenu' 10", out)
        self.assertNotIn("wait_state 'match message leaguefixtures league gamemenu' 25", out)

    def test_changed_navigation_shape_is_rejected(self):
        with self.assertRaises(ValueError):
            harden_match_navigation('echo changed')


if __name__ == '__main__':
    unittest.main()
