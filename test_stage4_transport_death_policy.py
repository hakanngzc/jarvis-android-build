import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


def load_module(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def composed_gate() -> str:
    live = load_module(
        'stage4_tools/prepare_stage4_live_input.py',
        'prepare_stage4_live_input_transport_death',
    )
    transport = load_module(
        'stage4_tools/prepare_stage4_transport_death.py',
        'prepare_stage4_transport_death_policy',
    )
    prepared = live.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))
    return transport.harden(prepared)


class Stage4TransportDeathPolicyTests(unittest.TestCase):
    def test_dead_emulator_transport_is_not_reported_as_gameplay_timeout(self):
        live_path = Path('stage4_tools/prepare_stage4_live_input.py')
        transport_path = Path('stage4_tools/prepare_stage4_transport_death.py')
        self.assertTrue(live_path.exists(), 'Stage4 live-input hardener must exist')
        self.assertTrue(transport_path.exists(), 'Stage4 transport-death hardener must exist')

        prepared = composed_gate()
        self.assertIn('set -euo pipefail', prepared)
        self.assertIn('EMULATOR_TRANSPORT_DEAD', prepared)
        self.assertIn('adb get-state', prepared)
        self.assertIn('emulator-transport-dead', prepared)
        self.assertIn('return 4', prepared)
        self.assertIn('transport_state" != device', prepared)
        self.assertIn('drive_live_chance "$cycle" "$elapsed"', prepared)
        self.assertNotIn('drive_live_chance "$cycle" "$elapsed" || true', prepared)

    def test_dead_transport_exits_live_driver_with_rc4_in_shell(self):
        prepared = composed_gate()
        start = prepared.index('capture_valid_live_frame(){')
        end = prepared.index('\n\nstart_game(){', start)
        live_functions = prepared[start:end]

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_bin = root / 'bin'
            fake_bin.mkdir()
            fake_adb = fake_bin / 'adb'
            fake_adb.write_text(
                '#!/bin/sh\n'
                '# Dead transport: screenshots/logcat/get-state all fail immediately.\n'
                'exit 1\n',
                encoding='utf-8',
            )
            fake_adb.chmod(0o755)

            work = root / 'work'
            out = root / 'out'
            work.mkdir()
            out.mkdir()
            flow = out / 'flow.log'
            shell = root / 'probe.sh'
            shell.write_text(
                '#!/usr/bin/env bash\n'
                'set -euo pipefail\n'
                f'WORK={work!s}\n'
                f'OUT={out!s}\n'
                f'FLOW={flow!s}\n'
                ': > "$FLOW"\n'
                + live_functions
                + '\n'
                'drive_live_chance 1 0\n'
                'echo SHOULD_NOT_REACH\n',
                encoding='utf-8',
            )
            shell.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            cp = subprocess.run(
                ['bash', str(shell)],
                cwd=Path.cwd(),
                env=env,
                text=True,
                capture_output=True,
                timeout=20,
                check=False,
            )

            self.assertEqual(cp.returncode, 4, cp.stdout + cp.stderr)
            self.assertNotIn('SHOULD_NOT_REACH', cp.stdout + cp.stderr)
            marker = out / 'emulator-transport-dead.txt'
            cycle_marker = out / 'cycle-1-emulator-transport-dead.txt'
            self.assertTrue(marker.exists(), cp.stdout + cp.stderr)
            self.assertTrue(cycle_marker.exists(), cp.stdout + cp.stderr)
            self.assertIn('EMULATOR_TRANSPORT_DEAD', marker.read_text(encoding='utf-8'))
            self.assertIn('EMULATOR_TRANSPORT_DEAD', flow.read_text(encoding='utf-8'))

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
        self.assertIn('if [ "$transport_state" != device ]; then', prepared)
        self.assertIn('return 1', prepared)
        self.assertIn('if [ "$rc" -ne 0 ]; then', prepared)
        self.assertIn('retrying on next match loop', prepared)


if __name__ == '__main__':
    unittest.main()
