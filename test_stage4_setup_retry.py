import unittest
from pathlib import Path


class Stage4SetupRetryTests(unittest.TestCase):
    def test_source_hash_failures_are_retryable_and_retry_cleans_previous_attempt(self):
        gate = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        runner = Path('stage4_tools/run_stage4_natural_gate.sh').read_text(encoding='utf-8')

        # Run #280 attempt 1 proved APKPure can transiently return bytes whose
        # SHA-256 does not match the verified NSS 4.31 stock XAPK. Treat source
        # integrity failures as setup-only, never as gameplay failures.
        self.assertIn("stock XAPK sha256 mismatch", gate)
        self.assertIn("exit 214", gate)
        self.assertIn("stock base APK sha256 mismatch", gate)
        self.assertIn("exit 215", gate)
        self.assertIn("214|215|218|219)", runner)

        # A retry after 218/219 can happen after an APK was installed with a
        # per-attempt CI key. The next attempt generates a new key, so the old
        # package and extracted/signing workspace must be removed first.
        self.assertIn("adb uninstall com.newstargames.newstarsoccer", runner)
        self.assertIn('rm -rf "${RUNNER_TEMP:?}/stage4-natural-work"', runner)

        retry_case = runner[runner.index('case "$rc" in'):runner.index('esac', runner.index('case "$rc" in'))]
        self.assertNotIn('220', retry_case)
        self.assertNotIn('221', retry_case)


if __name__ == '__main__':
    unittest.main()
