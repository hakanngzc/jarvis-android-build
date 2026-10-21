#!/usr/bin/env python3
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


class Stage3StarManStateTest(unittest.TestCase):
    def current_state_fn(self):
        script = Path('stage3_minimal_gate.sh').read_text(encoding='utf-8')
        match = re.search(r'current_state\(\)\{\n(.*?)\n\}\nwait_state\(\)', script, re.S)
        self.assertIsNotNone(match, 'current_state() function not found')
        return 'current_state(){\n' + match.group(1) + '\n}\n'

    def run_state(self, log_text):
        current_state_fn = self.current_state_fn()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fakebin = root / 'bin'
            work = root / 'work'
            fakebin.mkdir(); work.mkdir()
            fake_log = root / 'state.log'
            fake_log.write_text(log_text, encoding='utf-8')
            adb = fakebin / 'adb'
            adb.write_text(
                '#!/usr/bin/env bash\n'
                'if [ "${1:-}" = logcat ]; then cat "$FAKE_LOG"; exit 0; fi\n'
                'if [ "${1:-}" = shell ] && [ "${2:-}" = dumpsys ]; then exit 0; fi\n'
                'exit 0\n',
                encoding='utf-8',
            )
            adb.chmod(0o755)
            runner = root / 'run.sh'
            runner.write_text(
                '#!/usr/bin/env bash\nset -euo pipefail\n'
                f'WORK={str(work)!r}\n' + current_state_fn + 'current_state\n',
                encoding='utf-8',
            )
            runner.chmod(0o755)
            env = os.environ.copy()
            env['PATH'] = str(fakebin) + os.pathsep + env.get('PATH', '')
            env['FAKE_LOG'] = str(fake_log)
            cp = subprocess.run([str(runner)], env=env, text=True, capture_output=True, check=True)
            return cp.stdout.strip()

    def test_plain_starman_is_classified(self):
        state = self.run_state(
            'I/[Monkey]: Create Screen:starman\n'
            'I/[Monkey]: SETTING ACTIVE: starman\n'
            'I/[Monkey]: SetActive: starman\n'
        )
        self.assertEqual(state, 'starman')

    def test_bottommessage_overlay_preserves_starman_parent(self):
        # Exact ordering observed in Stage3 stock simulation run 39672454504.
        state = self.run_state(
            'I/[Monkey]: Create Screen:starman\n'
            'I/[Monkey]: SETTING ACTIVE: starman\n'
            'I/[Monkey]: SetActive: starman\n'
            'I/[Monkey]: SETTING ACTIVE: bottommessageachievement\n'
        )
        self.assertEqual(state, 'starman')


class Stage3StarManFlowTest(unittest.TestCase):
    def test_post_match_flow_accepts_and_advances_starman(self):
        patch = Path('stage3_match_flow_patch.py').read_text(encoding='utf-8')
        self.assertIn(' starman ', patch, 'post-match state sets must include starman')
        m = re.search(r'starman\)\n(.*?)\n\s*;;', patch, re.S)
        self.assertIsNotNone(m, 'post-match state machine must handle starman')
        handler = m.group(1)
        self.assertIn('press_play 3', handler)
        self.assertNotIn(
            'clear_log', handler,
            'starman retry must preserve parent evidence while bottom-message overlays consume taps',
        )


if __name__ == '__main__':
    unittest.main()
