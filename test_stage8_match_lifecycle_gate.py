#!/usr/bin/env python3
import re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

class Stage8MatchLifecycleGateTests(unittest.TestCase):
    def setUp(self):
        self.shell=(ROOT/'stage8_match_lifecycle_gate.sh').read_text(encoding='utf-8')
        self.workflow=(ROOT/'.github/workflows/nss-stage8-match-lifecycle.yml').read_text(encoding='utf-8') if (ROOT/'.github/workflows/nss-stage8-match-lifecycle.yml').exists() else ''

    def test_uses_unpatched_stage7_career_base_for_match(self):
        self.assertIn('"$ST7/signed/base-career.apk"',self.shell)
        self.assertNotIn('patch_stage3_fast_match_probe',self.shell)
        self.assertNotIn('patch_stage8_age_unlock',self.shell)

    def test_initial_gamemenu_to_leaguefixtures_uses_direct_screen_wait(self):
        marker='# Reach a real Career fixture using the stock route.'
        self.assertIn(marker,self.shell)
        block=self.shell.split(marker,1)[1].split('MATCH_REACHED=0',1)[0]
        self.assertIn("wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures'",block)
        self.assertIn("capture_log 'failed GameMenu -> LeagueFixtures'",block)
        self.assertNotIn("wait_state 'leaguefixtures message gamemenu'",block)

    def test_leaguefixtures_advance_uses_fixture_button_center_not_gamemenu_play(self):
        self.assertIn('press_fixture_play(){ press_logical 553 900',self.shell)
        loop=self.shell.split('MATCH_REACHED=0',1)[1].split('[ "$MATCH_REACHED" -eq 1 ]',1)[0]
        self.assertIn('leaguefixtures) press_fixture_play 3',loop)
        self.assertNotIn('leaguefixtures|gamemenu|league) press_play 3',loop)

    def test_background_foreground_keeps_same_process(self):
        self.assertIn('input keyevent 3',self.shell)
        self.assertIn('[ "$pid_before" = "$pid_bg" ]',self.shell)
        self.assertIn('[ "$pid_before" = "$pid_fg" ]',self.shell)
        self.assertIn('wait_resumed 20',self.shell)

    def test_resumed_match_must_continue_naturally_to_matchstats(self):
        self.assertIn('natural_input_burst',self.shell)
        self.assertIn('MATCHSTATS_REACHED',self.shell)
        self.assertIn('STAGE8_MATCH_LIFECYCLE_PASS',self.shell)
        self.assertNotIn('m_StartMatch',self.shell.split('# Start the untouched live match',1)[1].split('# Prove the resumed live match',1)[0])

    def test_all_adb_calls_are_bounded(self):
        m=re.search(r'adb\(\)\s*\{(?P<body>.*?)\n\}',self.shell,re.S)
        self.assertIsNotNone(m)
        self.assertIn('timeout --signal=TERM --kill-after=5s 45s',m.group('body'))

    def test_workflow_reuses_stage7_then_match_lifecycle(self):
        self.assertIn('bash stage7_runtime_gate.sh',self.workflow)
        self.assertIn('bash stage8_match_lifecycle_gate.sh',self.workflow)
        self.assertLess(self.workflow.index('bash stage7_runtime_gate.sh'),self.workflow.index('bash stage8_match_lifecycle_gate.sh'))
        self.assertIn('api-level: 29',self.workflow)

if __name__=='__main__':unittest.main()
