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


class Stage4TransportRuntimeTests(unittest.TestCase):
    def test_dead_transport_creates_runtime_marker_without_waiting_for_match_timeout(self):
        live = load_module(
            'stage4_tools/prepare_stage4_live_input.py',
            'prepare_stage4_live_input_dead_transport_runtime',
        )
        prepared = live.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))
        self.assertIn('exit 222', prepared)
        self.assertIn('runtime-transport-dead.txt', prepared)

        start = prepared.index('transport_health_check(){')
        end = prepared.index('\n\nstart_game(){', start)
        live_functions = prepared[start:end]

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fake_bin = root / 'bin'
            fake_bin.mkdir()
            fake_adb = fake_bin / 'adb'
            fake_adb.write_text('#!/bin/sh\nexit 1\n', encoding='utf-8')
            fake_adb.chmod(0o755)

            work = root / 'work'
            out = root / 'out'
            work.mkdir()
            out.mkdir()
            flow = out / 'flow.log'
            probe = root / 'probe.sh'
            probe.write_text(
                '#!/usr/bin/env bash\n'
                'set -u\n'
                f'WORK={work!s}\n'
                f'OUT={out!s}\n'
                f'FLOW={flow!s}\n'
                ': > "$FLOW"\n'
                + live_functions
                + '\n'
                'start=$(date +%s)\n'
                'set +e\n'
                'drive_live_chance 1 0\n'
                'rc=$?\n'
                'set -e\n'
                'elapsed=$(( $(date +%s) - start ))\n'
                'printf "rc=%s elapsed=%s\\n" "$rc" "$elapsed"\n'
                'test "$rc" -eq 1\n'
                'test "$elapsed" -lt 20\n'
                'test -s "$OUT/runtime-transport-dead.txt"\n'
                'grep -q STAGE4_EMULATOR_TRANSPORT_DEAD "$OUT/runtime-transport-dead.txt"\n'
                'grep -q STAGE4_EMULATOR_TRANSPORT_DEAD "$FLOW"\n',
                encoding='utf-8',
            )
            probe.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = f'{fake_bin}:{env["PATH"]}'
            cp = subprocess.run(
                ['bash', str(probe)],
                cwd=Path.cwd(),
                env=env,
                text=True,
                capture_output=True,
                timeout=25,
                check=False,
            )
            self.assertEqual(cp.returncode, 0, cp.stdout + cp.stderr)
            self.assertIn('rc=1', cp.stdout)


if __name__ == '__main__':
    unittest.main()
