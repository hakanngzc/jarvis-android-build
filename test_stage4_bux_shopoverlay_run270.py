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
    def test_run270_bux_exit_closes_both_overlays_then_restores_verified_gamemenu(self):
        module = load_module(
            'stage4_tools/prepare_stage4_event_navigation.py',
            'prepare_stage4_event_navigation_run270_shopoverlay',
        )
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        # Run #270 proves the actual stack: GameMenu is active immediately before
        # BuxOverlay, closing Bux publishes no ShopOverlay active marker, and the
        # next blind Play hits shopoverlay.buy. Therefore the deterministic stock
        # escape is X (Bux) -> Android Back (silent ShopOverlay) -> GameMenu state.
        self.assertIn('*shopoverlay*) echo shopoverlay;;', prepared)
        self.assertIn('stock ShopOverlay under Bux -> Android Back', prepared)
        self.assertIn(
            'adb shell input touchscreen tap "$x" "$y" </dev/null || true\n  sleep 2\n  echo "stock ShopOverlay under Bux -> Android Back" >> "$FLOW"\n  adb shell input keyevent 4 </dev/null || true',
            prepared,
        )
        self.assertEqual(
            prepared.count('buxoverlay) dismiss_stage4_bux_overlay || return 1; state=gamemenu;;'),
            2,
        )

        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_cycle10_skills_shop_overlay_closes_once_then_restores_gamemenu(self):
        module = load_module(
            'stage4_tools/prepare_stage4_event_navigation.py',
            'prepare_stage4_event_navigation_cycle10_skills_shopoverlay',
        )
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        # Natural run 40344874221 proves SkillsShopOverlay is a silent overlay
        # over GameMenu after OldProBoots -> PurchaseAnim -> information.btn_Back.
        # One Android Back closes the overlay without publishing a new state;
        # a second Back exits GameMenu to MainMenu. Track this overlay separately
        # and restore the already-proven underlying GameMenu after exactly one Back.
        self.assertIn('*skillsshopoverlay*) echo skillsshopoverlay;;', prepared)
        self.assertLess(
            prepared.index('*skillsshopoverlay*) echo skillsshopoverlay;;'),
            prepared.index('*shopoverlay*) echo shopoverlay;;'),
        )
        self.assertEqual(
            prepared.count('skillsshopoverlay) adb shell input keyevent 4 </dev/null || true; sleep 2; state=gamemenu;;'),
            2,
        )
        self.assertEqual(
            prepared.count('shopoverlay) adb shell input keyevent 4 </dev/null || true; sleep 2;;'),
            2,
        )
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_run284_bottom_message_achievement_keeps_matchstats_play_route(self):
        module = load_module(
            'stage4_tools/prepare_stage4_event_navigation.py',
            'prepare_stage4_event_navigation_run284_bottommessageachievement',
        )
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        # Run #284 proves bottommessageachievement can become the newest log marker
        # while MatchStats is still the actionable underlying screen. Treating it
        # as generic message sends the message-accept coordinate, dismisses the
        # achievement, and then hits skills.btn_Ratings on the silently exposed
        # screen. Run #254 proves stock Play on the same achievement state reaches
        # matchstats.btn_Play -> PlayToDate -> leaguefixtures instead.
        self.assertIn('*bottommessageachievement*) echo bottommessageachievement;;', prepared)
        self.assertLess(
            prepared.index('*bottommessageachievement*) echo bottommessageachievement;;'),
            prepared.index('*message*) echo message;;'),
        )
        self.assertEqual(
            prepared.count('bottommessageachievement) press_play 2;;'),
            2,
        )
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)


if __name__ == '__main__':
    unittest.main()
