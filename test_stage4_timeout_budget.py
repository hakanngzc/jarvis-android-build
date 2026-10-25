import unittest
from pathlib import Path


class Stage4TimeoutBudgetTests(unittest.TestCase):
    def test_natural_runtime_allows_bounded_long_live_matches(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        self.assertIn('timeout-minutes: 360', text)
        self.assertIn("MATCH_TIMEOUT_SECONDS: '900'", text)
        # This change is harness patience only; it must never become a shortcut
        # around the natural Career/match/season path.
        for forbidden in (
            'm_sdate = 365',
            'm_sdate=365',
            'p_NewSeason(',
            'm_skipMatches',
            'm_Simulate',
            'patch_stage3_fast_match_probe.py',
        ):
            self.assertNotIn(forbidden, text)


if __name__ == '__main__':
    unittest.main()
