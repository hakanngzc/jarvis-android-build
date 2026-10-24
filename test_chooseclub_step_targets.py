import unittest
from pathlib import Path


class ChooseClubStepTargetTests(unittest.TestCase):
    def test_pixel4_setup_targets_are_step_specific(self):
        text = Path('stage2_residual_tools/prepare_chooseclub_visual.py').read_text(encoding='utf-8')
        self.assertIn('fresh-setup-ok-1', text)
        self.assertIn('tap 805 1845', text, 'Welcome/help checkmark must use the raw run132 PNG measured center')
        self.assertIn('x=560..1050, y=1714..1978', text,
                      'keep the artifact measurement that justifies the Welcome target')
        self.assertIn('fresh-setup-ok-3', text)
        self.assertIn('tap 940 1830', text, 'player-profile Next must use the measured arrow-center target')
        self.assertIn('Pixel4 player-profile Next target 940,1830', text)
        self.assertNotIn('tap 620 1425', text, 'discard the previously mis-scaled Welcome target')


if __name__ == '__main__':
    unittest.main()
