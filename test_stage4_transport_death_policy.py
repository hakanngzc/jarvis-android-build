import importlib.util
import unittest
from pathlib import Path


def load_module(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class Stage4TransportDeathPolicyTests(unittest.TestCase):
    def test_dead_emulator_transport_is_not_reported_as_gameplay_timeout(self):
        p = Path('stage4_tools/prepare_stage4_live_input.py')
        self.assertTrue(p.exists(), 'Stage4 live-input hardener must exist')
        module = load_module(str(p), 'prepare_stage4_live_input_transport_death')
        prepared = module.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))

        # run328 attempt1 proved a distinct failure mode: the match had started,
        # then every screenshot became invalid and emulator-5554 disappeared.
        # The harness must classify that infrastructure failure separately from
        # an ordinary 900s gameplay timeout without mutating game/season state.
        self.assertIn('EMULATOR_TRANSPORT_DEAD', prepared)
        self.assertIn('adb get-state', prepared)
        self.assertIn('emulator-transport-dead', prepared)
        self.assertIn('return 4', prepared)


if __name__ == '__main__':
    unittest.main()
