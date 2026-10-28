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

    def test_initial_gamemenu_to_leaguefixtures_requires_real_activation(self):
        marker='# Reach a real Career fixture using the stock route.'
        self.assertIn(marker,self.shell)
        block=self.shell.split(marker,1)[1].split('MATCH_REACHED=0',1)[0]
        self.assertIn("wait_log 'SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures'",block)
        self.assertNotIn("wait_log 'Create Screen:[[:space:]]*leaguefixtures",block)
        self.assertIn("capture_log 'failed GameMenu -> LeagueFixtures'",block)
        self.assertNotIn("wait_state 'leaguefixtures message gamemenu'",block)

    def test_message_fallback_requires_real_active_message(self):
        block=self.shell.split('# Reach a real Career fixture using the stock route.',1)[1].split('MATCH_REACHED=0',1)[0]
        self.assertIn("grep -qiE 'SETTING ACTIVE:[[:space:]]*message|SetActive:[[:space:]]*message'",block)
        self.assertNotIn("grep -qiE 'Create Screen:[[:space:]]*message",block)

    def test_current_state_ignores_create_screen_preallocation(self):
        block=self.shell.split('current_state(){',1)[1].split('wait_state(){',1)[0]
        self.assertIn("grep -Ei 'SETTING ACTIVE:|SetActive:'",block)
        self.assertNotIn('Create Screen:',block)

    def test_gamemenu_and_match_play_use_proven_bottom_right_coordinate(self):
        self.assertIn('press_play(){ press_logical 553 900',self.shell)
        self.assertNotIn('press_play(){ press_logical 553 829',self.shell)

    def test_leaguefixtures_advance_uses_fixture_button_center_not_gamemenu_play(self):
        self.assertIn('press_fixture_play(){ press_logical 553 900',self.shell)
        loop=self.shell.split('MATCH_REACHED=0',1)[1].split('[ "$MATCH_REACHED" -eq 1 ]',1)[0]
        self.assertIn('leaguefixtures) press_fixture_play 3',loop)
        self.assertNotIn('leaguefixtures|gamemenu|league) press_play 3',loop)

    def test_screen_geometry_is_cached_once_for_natural_input_loop(self):
        self.assertIn('WM_SIZE="$(adb shell wm size',self.shell)
        logical=self.shell.split('logical_xy(){',1)[1].split('press_physical(){',1)[0]
        self.assertIn('sys.argv[3]',logical)
        self.assertNotIn("subprocess.check_output(['adb','shell','wm','size']",logical)

    def test_match_entry_trace_records_each_step_and_runtime_event(self):
        self.assertIn('ENTRY_TRACE="$OUT/STAGE8_MATCH_ENTRY_TRACE.txt"',self.shell)
        self.assertIn(': > "$ENTRY_TRACE"',self.shell)
        loop=self.shell.split('MATCH_REACHED=0',1)[1].split('[ "$MATCH_REACHED" -eq 1 ]',1)[0]
        self.assertIn('echo "step=$step before=$state" >> "$ENTRY_TRACE"',loop)
        self.assertIn("grep -Ei 'HitGadget:|SETTING ACTIVE:|SetActive:|Create Screen:'",loop)
        self.assertIn('echo "step=$step after=$state last=${last_event:-NONE}" >> "$ENTRY_TRACE"',loop)

    def test_live_match_start_dismisses_tutorial_until_real_play_gadget_hits(self):
        self.assertIn('start_live_match(){',self.shell)
        self.assertIn("HitGadget:[[:space:]]*match\\.btn_Play",self.shell)
        self.assertIn('start_live_match',self.shell.split('# Start the untouched live match',1)[1].split('# Prove the resumed live match',1)[0])

    def test_background_foreground_keeps_same_process(self):
        self.assertIn('input keyevent 3',self.shell)
        self.assertIn('[ "$pid_before" = "$pid_bg" ]',self.shell)
        self.assertIn('[ "$pid_before" = "$pid_fg" ]',self.shell)
        self.assertIn('wait_resumed 20',self.shell)

    def test_background_foreground_waits_for_nonblack_render_before_inputs(self):
        self.assertIn('wait_rendered_frame(){',self.shell)
        lifecycle=self.shell.split('# Start the untouched live match',1)[1].split('# Prove the resumed live match',1)[0]
        self.assertIn('wait_resumed 20',lifecycle)
        self.assertIn('wait_rendered_frame 30',lifecycle)
        self.assertLess(lifecycle.index('wait_resumed 20'),lifecycle.index('wait_rendered_frame 30'))
        self.assertLess(lifecycle.index('wait_rendered_frame 30'),lifecycle.index('capture_log \'live match background -> foreground\''))

    def test_natural_match_loop_uses_event_gated_live_driver(self):
        self.assertIn('drive_live_chance(){',self.shell)
        self.assertIn("SETTING ACTIVE:[[:space:]]*(matchminigame|tapball)",self.shell)
        self.assertIn('stage4_tools/classify_live_frame.py',self.shell)
        loop=self.shell.split('# Prove the resumed live match remains functional',1)[1].split('[ "$MATCHSTATS_REACHED" -eq 1 ]',1)[0]
        self.assertIn('drive_live_chance "$cycle"',loop)
        self.assertNotIn('natural_input_burst',loop)
        self.assertNotIn('match|unknown) press_play',loop)

    def test_resumed_match_must_continue_naturally_to_matchstats(self):
        self.assertIn('drive_live_chance',self.shell)
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
