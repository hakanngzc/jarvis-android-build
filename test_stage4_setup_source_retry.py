import unittest
from pathlib import Path


class Stage4SetupSourceRetryTests(unittest.TestCase):
    def test_only_verified_stock_hash_mismatch_is_promoted_to_retryable_setup_rc(self):
        runner = Path('stage4_tools/run_stage4_natural_gate.sh').read_text(encoding='utf-8')
        self.assertIn('stock_source_mismatch(){', runner)
        self.assertIn("sed -n \"s/^XAPK_SHA='\\([^']*\\)'.*/\\1/p\" \"$GATE\"", runner)
        self.assertIn("sed -n \"s/^BASE_SHA='\\([^']*\\)'.*/\\1/p\" \"$GATE\"", runner)
        self.assertIn('sha256sum "$xapk"', runner)
        self.assertIn('sha256sum "$base"', runner)
        self.assertIn('if [ "$rc" -eq 1 ] && stock_source_mismatch; then', runner)
        self.assertIn('rc=219', runner)
        self.assertNotIn('if [ "$rc" -eq 1 ]; then rc=219', runner)

    def test_retry_clears_only_disposable_setup_work(self):
        runner = Path('stage4_tools/run_stage4_natural_gate.sh').read_text(encoding='utf-8')
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


if __name__ == '__main__':
    unittest.main()
