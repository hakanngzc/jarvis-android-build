import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


RUNNER = Path('stage4_tools/run_stage4_natural_gate.sh')


class Stage4SetupSourceRetryTests(unittest.TestCase):
    def test_only_verified_stock_hash_mismatch_is_promoted_to_retryable_setup_rc(self):
        runner = RUNNER.read_text(encoding='utf-8')
        self.assertIn('stock_source_mismatch(){', runner)
        self.assertIn("sed -n \"s/^XAPK_SHA='\\([^']*\\)'.*/\\1/p\" \"$GATE\"", runner)
        self.assertIn("sed -n \"s/^BASE_SHA='\\([^']*\\)'.*/\\1/p\" \"$GATE\"", runner)
        self.assertIn('sha256sum "$xapk"', runner)
        self.assertIn('sha256sum "$base"', runner)
        self.assertIn('if [ "$rc" -eq 1 ] && stock_source_mismatch; then', runner)
        self.assertIn('rc=219', runner)
        self.assertNotIn('if [ "$rc" -eq 1 ]; then rc=219', runner)

    def test_retry_clears_only_disposable_setup_work(self):
        runner = RUNNER.read_text(encoding='utf-8')
        retry_case = runner[runner.index('case "$rc" in'):runner.index('esac', runner.index('case "$rc" in'))]
        self.assertIn('218|219)', retry_case)
        self.assertIn('rm -rf "${RUNNER_TEMP:?}/stage4-natural-work"', retry_case)
        self.assertNotIn('220', retry_case)
        self.assertNotIn('221', retry_case)

    def test_gate_keeps_exact_stock_hashes_and_forbidden_shortcuts_absent(self):
        gate = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        self.assertIn("XAPK_SHA='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'", gate)
        self.assertIn("BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'", gate)
        self.assertEqual(gate.count('sha256sum -c -'), 2)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, gate)

    def test_real_hash_mismatch_retries_three_times_then_returns_219(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gate = root / 'mismatch_gate.sh'
            gate.write_text(textwrap.dedent('''\
                #!/usr/bin/env bash
                set -euo pipefail
                WORK="${RUNNER_TEMP:?}/stage4-natural-work"
                XAPK_SHA='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                BASE_SHA='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
                mkdir -p "$WORK"
                printf 'bad-stock' > "$WORK/nss431.xapk"
                exit 1
            '''), encoding='utf-8')
            gate.chmod(0o755)
            env = os.environ.copy()
            env['RUNNER_TEMP'] = str(root)
            proc = subprocess.run(['bash', str(RUNNER), str(gate)], text=True, capture_output=True, env=env)
            self.assertEqual(proc.returncode, 219, proc.stdout + proc.stderr)
            retry_log = root / 'stage4-natural' / 'setup-retries.log'
            self.assertEqual(len(retry_log.read_text(encoding='utf-8').splitlines()), 3)
            self.assertFalse((root / 'stage4-natural-work').exists())

    def test_generic_rc1_is_not_retried(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gate = root / 'generic_gate.sh'
            gate.write_text(textwrap.dedent('''\
                #!/usr/bin/env bash
                set -euo pipefail
                XAPK_SHA='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
                BASE_SHA='bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'
                exit 1
            '''), encoding='utf-8')
            gate.chmod(0o755)
            env = os.environ.copy()
            env['RUNNER_TEMP'] = str(root)
            proc = subprocess.run(['bash', str(RUNNER), str(gate)], text=True, capture_output=True, env=env)
            self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
            self.assertEqual(proc.stdout.count('Stage4 natural gate setup attempt'), 1)
            self.assertFalse((root / 'stage4-natural' / 'setup-retries.log').exists())


if __name__ == '__main__':
    unittest.main()
