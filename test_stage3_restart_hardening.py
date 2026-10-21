import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
HARNESS = ROOT / 'stage3_harness.py'
READINESS = ROOT / 'stage3_readiness_patch.py'
RETRY = ROOT / 'stage3_career_input_retry_patch.py'


class Stage3RestartHardeningTests(unittest.TestCase):
    def load_harness(self):
        spec = importlib.util.spec_from_file_location('stage3_harness', HARNESS)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_mainmenu_is_a_real_harness_state(self):
        mod = self.load_harness()
        self.assertEqual(
            mod.detect_state('I/[Monkey]: SETTING ACTIVE: mainmenu\n')['state'],
            'mainmenu',
        )

    def test_readiness_uses_live_window_state_not_stale_starting_flag(self):
        src = READINESS.read_text(encoding='utf-8')
        self.assertIn('Splash Screen', src)
        self.assertIn('mObscured=false', src)
        self.assertIn('mObscuringWindow=null', src)
        self.assertNotIn("! grep -q 'STARTING_WINDOW_SHOWN'", src)
        self.assertIn('touch-ready', src)

    def test_career_retry_aborts_on_fatal_instead_of_pressing_again(self):
        src = RETRY.read_text(encoding='utf-8')
        self.assertIn('fatal_rc', src)
        self.assertIn('aborting Career retry', src)
        self.assertIn('current_state', src)
        self.assertIn('mainmenu', src)


if __name__ == '__main__':
    unittest.main()
