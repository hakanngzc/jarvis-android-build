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


class Stage4OfflineRuntimeTests(unittest.TestCase):
    def test_offline_preparer_isolates_external_ads_without_game_state_patch(self):
        p = Path('stage4_tools/prepare_stage4_offline_runtime.py')
        self.assertTrue(p.exists())
        module = load_module(str(p), 'prepare_stage4_offline_runtime')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('settings put global airplane_mode_on 1', prepared)
        self.assertIn('svc wifi disable', prepared)
        self.assertIn('svc data disable', prepared)
        self.assertIn('ip link set eth0 down', prepared)
        self.assertIn('STAGE4_EXTERNAL_NETWORK_DISABLED=1', prepared)
        self.assertLess(prepared.index('STAGE4_EXTERNAL_NETWORK_DISABLED=1'), prepared.index('start_game fresh'))
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_offline_preparer_marks_stock_source_hash_mismatch_as_retryable_setup_failure(self):
        p = Path('stage4_tools/prepare_stage4_offline_runtime.py')
        module = load_module(str(p), 'prepare_stage4_offline_runtime_source_retry')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        self.assertIn('stock XAPK checksum mismatch; retryable setup failure', prepared)
        self.assertIn('stock base APK checksum mismatch; retryable setup failure', prepared)
        self.assertIn('exit 219', prepared)
        self.assertNotIn('echo "$XAPK_SHA  $WORK/nss431.xapk" | sha256sum -c -\nunzip -q', prepared)
        self.assertNotIn('BASE="$WORK/xapk/com.newstargames.newstarsoccer.apk"; echo "$BASE_SHA  $BASE" | sha256sum -c -\nPYTHONPATH=', prepared)

        runner = Path('stage4_tools/run_stage4_natural_gate.sh').read_text(encoding='utf-8')
        self.assertIn('218|219)', runner)
        retry_case = runner[runner.index('case "$rc" in'):runner.index('esac', runner.index('case "$rc" in'))]
        self.assertNotIn('220', retry_case)
        self.assertNotIn('221', retry_case)

    def test_workflow_applies_offline_isolation_before_short_league(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        offline = 'stage4_tools/prepare_stage4_offline_runtime.py'
        short = 'stage4_tools/prepare_stage4_short_league.py'
        self.assertIn(offline, text)
        self.assertIn(short, text)
        self.assertLess(text.index(offline), text.index(short))
        self.assertIn('stage4-natural-gate.offline.sh', text)


if __name__ == '__main__':
    unittest.main()
