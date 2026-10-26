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
    def test_run270_bux_exit_tracks_underlying_shopoverlay_and_backs_out(self):
        module = load_module(
            'stage4_tools/prepare_stage4_event_navigation.py',
            'prepare_stage4_event_navigation_run270_shopoverlay',
        )
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        # Run #270: BuxOverlay X produced HitGadget: WTF, then the next blind Play
        # produced HitGadget: shopoverlay.buy and reopened/stayed in the purchase UI.
        # Therefore the Bux overlay must not be treated as an unconditional GameMenu
        # transition; the underlying ShopOverlay is a real stock navigation state.
        self.assertIn('*shopoverlay*) echo shopoverlay;;', prepared)
        self.assertEqual(
            prepared.count('shopoverlay) adb shell input keyevent 4 </dev/null || true; sleep 2;;'),
            2,
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
