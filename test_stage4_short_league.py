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


class Stage4ShortLeagueTests(unittest.TestCase):
    def test_preparer_selects_andorra_only_through_stock_ui(self):
        p = Path('stage4_tools/prepare_stage4_short_league.py')
        self.assertTrue(p.exists())
        module = load_module(str(p), 'prepare_stage4_short_league')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('press_logical 320 640 2', prepared)
        self.assertIn('press_logical 320 400 2', prepared)
        self.assertIn('short-league-andorra-selected', prepared)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_workflow_applies_short_league_before_prematch(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        short = 'stage4_tools/prepare_stage4_short_league.py'
        prematch = 'stage4_tools/prepare_stage4_prematch.py'
        self.assertIn(short, text)
        self.assertIn(prematch, text)
        self.assertLess(text.index(short), text.index(prematch))
        self.assertIn('stage4-natural-gate.shortleague.sh', text)


if __name__ == '__main__':
    unittest.main()
