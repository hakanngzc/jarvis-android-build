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


class Stage4TimeoutBudgetTests(unittest.TestCase):
    def test_natural_runtime_allows_bounded_long_live_matches(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        self.assertIn('timeout-minutes: 360', text)
        self.assertIn("MATCH_TIMEOUT_SECONDS: '900'", text)
        self.assertIn("MIN_MATCH_CYCLES: '12'", text)
        self.assertIn("MIN_WALL_SECONDS: '1200'", text)
        self.assertNotIn("MIN_MATCH_CYCLES: '1'", text)
        self.assertNotIn("MIN_WALL_SECONDS: '0'", text)
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

    def test_run290_navigation_dismisses_stock_facebook_webview_detour(self):
        hardener = load_module(
            'stage4_tools/prepare_stage4_live_input.py',
            'prepare_stage4_live_input_run290_facebook_webview',
        )
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)

        # Natural run #290 completed 20 matches, then FacebookLike launched the
        # stock Android WebView Browser Tester in the foreground. NSS remained
        # paused underneath while blind GameMenu Play taps were sent to the
        # browser. The Career navigation guard must close only this proven
        # external activity with Android Back before clearing NSS logcat.
        self.assertIn('org.chromium.webview_shell/.WebViewBrowserActivity', prepared)
        self.assertIn('foreground Facebook WebView detected; Android Back', prepared)
        self.assertIn('dismiss_external_browser_if_present "$step"', prepared)
        guard = prepared.index('dismiss_external_browser_if_present "$step"')
        clear = prepared.index('clear_log', guard)
        self.assertLess(guard, clear)

        for forbidden in (
            'm_sdate = 365',
            'm_sdate=365',
            'p_NewSeason(',
            'm_skipMatches',
            'm_Simulate',
        ):
            self.assertNotIn(forbidden, prepared)


if __name__ == '__main__':
    unittest.main()
