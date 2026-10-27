import unittest
from pathlib import Path


class Stage4EmulatorPinPolicyTests(unittest.TestCase):
    def test_natural_full_season_pins_emulator_3711_only_for_stage4(self):
        workflow = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')

        self.assertEqual(workflow.count('emulator-build: 15917651'), 1)
        self.assertNotIn('emulator/emulator" -version', workflow)
        stage2, stage4 = workflow.split('  stage4-natural-runtime:', 1)
        self.assertNotIn('emulator-build:', stage2)
        self.assertIn('emulator-build: 15917651', stage4)
        self.assertIn('test_stage4_emulator_pin_policy.py', workflow)
        self.assertIn('test_stage4_transport_runtime.py', workflow)


if __name__ == '__main__':
    unittest.main()
