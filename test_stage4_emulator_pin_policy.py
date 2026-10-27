import unittest
from pathlib import Path


class Stage4EmulatorPinPolicyTests(unittest.TestCase):
    def test_natural_full_season_pins_verified_emulator_build_and_transport_classifier(self):
        workflow = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')

        self.assertIn('emulator-build: 15917651', workflow)
        self.assertIn('"$ANDROID_HOME/emulator/emulator" -version', workflow)
        self.assertIn('Android emulator version 37\\.1\\.11\\.0', workflow)
        self.assertIn('build_id 15917651', workflow)
        self.assertIn('prepare_stage4_transport_death.py', workflow)
        self.assertIn('test_stage4_transport_death_policy.py', workflow)
        self.assertIn('test_stage4_emulator_pin_policy.py', workflow)

        live_index = workflow.index('prepare_stage4_live_input.py "$RUNNER_TEMP/stage4-natural-gate.prematch.sh"')
        transport_index = workflow.index('prepare_stage4_transport_death.py "$RUNNER_TEMP/stage4-natural-gate.live.sh"')
        speed_index = workflow.index('prepare_stage4_match_speed.py "$RUNNER_TEMP/stage4-natural-gate.transport.sh"')
        self.assertLess(live_index, transport_index)
        self.assertLess(transport_index, speed_index)


if __name__ == '__main__':
    unittest.main()
