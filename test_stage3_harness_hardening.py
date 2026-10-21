import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
MODULE = ROOT / 'stage3_harness.py'


class Stage3HarnessHardeningTests(unittest.TestCase):
    def load(self):
        self.assertTrue(MODULE.exists(), 'stage3_harness.py must exist')
        spec = importlib.util.spec_from_file_location('stage3_harness', MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_matchreview_internal_weekly_phase_uses_gameplay_signal(self):
        mod = self.load()
        log = '\n'.join([
            'I/[Monkey]: Create Screen:matchreview',
            'I/[Monkey]: SETTING ACTIVE: matchreview',
            'I/[Monkey]: SetActive: matchreview',
            'I/[Monkey]: USE player.matchReviewBuxAwarded: 0',
            'I/[Monkey]: Award Currency 1',
        ])
        result = mod.detect_state(log)
        self.assertEqual(result['state'], 'weeklyreport')

    def test_later_gamemenu_overrides_weekly_phase(self):
        mod = self.load()
        log = '\n'.join([
            'I/[Monkey]: SetActive: matchreview',
            'I/[Monkey]: Award Currency 1',
            'I/[Monkey]: SetActive: gamemenu',
        ])
        self.assertEqual(mod.detect_state(log)['state'], 'gamemenu')

    def test_matchover_is_fulltime_without_new_screen(self):
        mod = self.load()
        log = 'I/[Monkey]: SetActive: match\nI/[Monkey]: MatchOver result=1\n'
        self.assertEqual(mod.detect_state(log)['state'], 'fulltime')

    def test_platform_anr_is_not_nss_fault(self):
        mod = self.load()
        self.assertEqual(mod.classify_failure('ANR in com.android.systemui', True), 'emulator')
        self.assertEqual(mod.classify_failure('ANR in com.google.android.apps.nexuslauncher', True), 'emulator')

    def test_nss_anr_is_nss_fault(self):
        mod = self.load()
        self.assertEqual(mod.classify_failure('ANR in com.newstargames.newstarsoccer', False), 'nss')


if __name__ == '__main__':
    unittest.main()
