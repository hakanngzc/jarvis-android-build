import os
import subprocess
import tempfile
import unittest
from pathlib import Path


RUNNER = Path('stage4_tools/run_stage4_natural_gate.sh').resolve()


def write_executable(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8')
    path.chmod(0o755)


class Stage4SetupRetryTests(unittest.TestCase):
    def test_source_hash_failures_are_retryable_and_retry_cleans_previous_attempt(self):
        runner = RUNNER.read_text(encoding='utf-8')

        # Run #280 attempt 1 proved APKPure can transiently return bytes whose
        # SHA-256 does not match the verified NSS 4.31 stock XAPK. The wrapper
        # should reinterpret only a generic rc=1 that is accompanied by a real
        # source-integrity mismatch; ordinary gameplay rc=1 must still fail.
        self.assertIn('XAPK_SHA=', runner)
        self.assertIn('BASE_SHA=', runner)
        self.assertIn('source-integrity XAPK mismatch -> retry rc=214', runner)
        self.assertIn('source-integrity base APK mismatch -> retry rc=215', runner)
        self.assertIn('214|215|218|219)', runner)

        # A retry after 218/219 can happen after an APK was installed with a
        # per-attempt CI key. The next attempt generates a new key, so the old
        # package and extracted/signing workspace must be removed first.
        self.assertIn('adb uninstall com.newstargames.newstarsoccer', runner)
        self.assertIn('rm -rf "${RUNNER_TEMP:?}/stage4-natural-work"', runner)

        retry_case = runner[runner.index('case "$rc" in'):runner.index('esac', runner.index('case "$rc" in'))]
        self.assertNotIn('220', retry_case)
        self.assertNotIn('221', retry_case)

    def test_bad_xapk_bytes_retry_once_and_start_with_clean_workdir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            write_executable(
                bin_dir / 'adb',
                '#!/bin/sh\necho "$*" >> "$RUNNER_TEMP/adb-calls.log"\nexit 0\n',
            )
            gate = root / 'gate.sh'
            write_executable(
                gate,
                '''#!/usr/bin/env bash
set -euo pipefail
COUNT="$RUNNER_TEMP/attempt-count"
n=0
[ -f "$COUNT" ] && n="$(cat "$COUNT")"
n=$((n + 1))
echo "$n" > "$COUNT"
if [ "$n" -eq 1 ]; then
  mkdir -p "$RUNNER_TEMP/stage4-natural-work"
  printf 'definitely-not-the-stock-xapk' > "$RUNNER_TEMP/stage4-natural-work/nss431.xapk"
  exit 1
fi
[ ! -e "$RUNNER_TEMP/stage4-natural-work/nss431.xapk" ] || exit 97
exit 0
''',
            )
            env = os.environ.copy()
            env['RUNNER_TEMP'] = str(root)
            env['PATH'] = f"{bin_dir}:{env.get('PATH', '')}"
            proc = subprocess.run(
                ['bash', str(RUNNER), str(gate)],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)
            self.assertEqual((root / 'attempt-count').read_text().strip(), '2')
            self.assertIn('source-integrity XAPK mismatch -> retry rc=214', proc.stdout)
            self.assertIn('setup-only retry after rc=214', (root / 'stage4-natural' / 'setup-retries.log').read_text())
            self.assertIn('uninstall com.newstargames.newstarsoccer', (root / 'adb-calls.log').read_text())

    def test_generic_rc1_without_source_mismatch_is_not_retried(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            gate = root / 'gate.sh'
            write_executable(
                gate,
                '''#!/usr/bin/env bash
COUNT="$RUNNER_TEMP/attempt-count"
n=0
[ -f "$COUNT" ] && n="$(cat "$COUNT")"
n=$((n + 1))
echo "$n" > "$COUNT"
exit 1
''',
            )
            env = os.environ.copy()
            env['RUNNER_TEMP'] = str(root)
            proc = subprocess.run(
                ['bash', str(RUNNER), str(gate)],
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                check=False,
            )
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertEqual((root / 'attempt-count').read_text().strip(), '1')
            self.assertNotIn('setup-only retry', proc.stdout)


if __name__ == '__main__':
    unittest.main()
