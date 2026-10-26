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


class Stage4Run270BuxShopOverlayRegression(unittest.TestCase):
    def test_run270_bux_exit_closes_silent_underlying_shopoverlay(self):
        module = load_module(
            'stage4_tools/prepare_stage4_event_navigation.py',
            'prepare_stage4_event_navigation_run270_shopoverlay',
        )
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        # Run #270 proved that tapping the visible BuxOverlay X does not publish a
        # SetActive/Create/SETTING ACTIVE marker for the underlying ShopOverlay.
        # The next blind Play tap hit shopoverlay.buy. Therefore the Bux handler
        # must close the silent underlying stock overlay itself instead of waiting
        # for latest_state() to discover a transition that is never published.
        self.assertIn('*shopoverlay*) echo shopoverlay;;', prepared)
        self.assertIn('stock ShopOverlay under Bux -> Android Back', prepared)
        self.assertIn(
            'adb shell input touchscreen tap "$x" "$y" </dev/null || true\n  sleep 2\n  echo "stock ShopOverlay under Bux -> Android Back" >> "$FLOW"\n  adb shell input keyevent 4 </dev/null || true',
            prepared,
        )
        self.assertNotIn(
            'buxoverlay) dismiss_stage4_bux_overlay || return 1; state=gamemenu;;',
            prepared,
        )
        self.assertEqual(
            prepared.count('buxoverlay) dismiss_stage4_bux_overlay || return 1;;'),
            2,
        )

        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)


if __name__ == '__main__':
    unittest.main()
