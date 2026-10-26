import unittest
from pathlib import Path


class Stage4SetupSourceRetryTests(unittest.TestCase):
    def test_stock_source_failures_are_bounded_retryable_setup_failures(self):
        gate = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        self.assertIn("curl -fL --retry 3 -A 'Mozilla/5.0' -e \"$REFERER\" \"$URL\" -o \"$WORK/nss431.xapk\" || exit 219", gate)
        self.assertEqual(gate.count('sha256sum -c - || exit 219'), 2)
        self.assertIn('unzip -q \"$WORK/nss431.xapk\" -d \"$WORK/xapk\" || exit 219', gate)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, gate)

    def test_retry_clears_only_disposable_setup_work(self):
        runner = Path('stage4_tools/run_stage4_natural_gate.sh').read_text(encoding='utf-8')
        retry_case = runner[runner.index('case \"$rc\" in'):runner.index('esac', runner.index('case \"$rc\" in'))]
        self.assertIn('218|219)', retry_case)
        self.assertIn('rm -rf \"${RUNNER_TEMP:?}/stage4-natural-work\"', retry_case)
        self.assertNotIn('stage4-natural\"', retry_case.split('rm -rf', 1)[1].split('\n', 1)[0])
        self.assertNotIn('220', retry_case)
        self.assertNotIn('221', retry_case)


if __name__ == '__main__':
    unittest.main()
