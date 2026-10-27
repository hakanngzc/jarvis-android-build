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
        live_path = Path('stage4_tools/prepare_stage4_live_input.py')
        transport_path = Path('stage4_tools/prepare_stage4_transport_death.py')
        self.assertTrue(live_path.exists(), 'Stage4 live-input hardener must exist')
        self.assertTrue(transport_path.exists(), 'Stage4 transport-death hardener must exist')

        live = load_module(str(live_path), 'prepare_stage4_live_input_transport_death')
        transport = load_module(str(transport_path), 'prepare_stage4_transport_death_policy')
        prepared = live.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))
        prepared = transport.harden(prepared)

        # run328 attempts 1 and 2 proved a distinct failure mode: a real match had
        # started, then every screenshot became invalid and emulator-5554 vanished.
        # The harness must classify that infrastructure failure separately from
        # an ordinary gameplay timeout without mutating game or season state.
        self.assertIn('EMULATOR_TRANSPORT_DEAD', prepared)
        self.assertIn('adb get-state', prepared)
        self.assertIn('emulator-transport-dead', prepared)
        self.assertIn('return 4', prepared)
        self.assertIn('transport_state" != device', prepared)

    def test_live_frame_failure_with_healthy_device_remains_retryable(self):
        transport = load_module(
            'stage4_tools/prepare_stage4_transport_death.py',
            'prepare_stage4_transport_death_retryable',
        )
        source = '''capture_valid_live_frame(){
  local final="$1" tmp attempt
  rm -f "$tmp"
  return 1
}

drive_live_chance(){
  local rc frame cycle elapsed
  if ! capture_valid_live_frame "$frame"; then
    echo "cycle $cycle valid live frame unavailable @${elapsed}s; retrying on next match loop" >> "$FLOW"
    sleep 1
    return 0
  fi
}
'''
        prepared = transport.harden(source)
        self.assertIn("if [ \"$transport_state\" != device ]; then", prepared)
        self.assertIn('return 1', prepared)
        self.assertIn('if [ "$rc" -ne 0 ]; then', prepared)
        self.assertIn('retrying on next match loop', prepared)


if __name__ == '__main__':
    unittest.main()
