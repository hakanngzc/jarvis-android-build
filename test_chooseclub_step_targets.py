import unittest
from pathlib import Path


class ChooseClubStepTargetTests(unittest.TestCase):
    def test_pixel4_setup_targets_are_step_specific(self):
        text = Path('stage2_residual_tools/prepare_chooseclub_visual.py').read_text(encoding='utf-8')
        self.assertIn('fresh-setup-ok-1', text)
        self.assertIn('tap 620 1425', text, 'Welcome/help checkmark target must remain explicit')
        self.assertIn('fresh-setup-ok-3', text)
        self.assertIn('tap 940 1830', text, 'player-profile Next must use the measured arrow-center target')
        self.assertIn('Pixel4 player-profile Next target 940,1830', text)
        self.assertNotIn('"$attempt" -eq 1', text,
                         'Welcome target must not be reused blindly on every later setup step')


if __name__ == '__main__':
    unittest.main()
