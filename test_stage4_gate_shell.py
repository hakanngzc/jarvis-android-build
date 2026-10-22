#!/usr/bin/env python3
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class Stage4GateShellRegressionTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / 'stage4_season_gate.sh').read_text(encoding='utf-8')

    def test_dump_save_does_not_expand_tag_in_same_local_statement(self):
        match = re.search(r'dump_save\(\)\{\n(?P<body>.*?)\n\}', self.text, re.S)
        self.assertIsNotNone(match, 'dump_save function not found')
        body = match.group('body')
        self.assertNotRegex(
            body,
            r'local\s+tag="\$1"[^\n]*\$\{tag\}',
            'set -u regression: tag is expanded in the same local statement that assigns it',
        )

    def test_slot0_press_is_bounded_and_verified_by_stock_hitgadget_signal(self):
        match = re.search(r'open_slot0\(\)\{\n(?P<body>.*?)\n\}', self.text, re.S)
        self.assertIsNotNone(match, 'open_slot0 function not found')
        body = match.group('body')
        self.assertIn('HitGadget: saveslot.btn_Slot0', body)
        self.assertRegex(body, r'for\s+slot_attempt\s+in\s+1\s+2\s+3')
        self.assertIn('Slot0 press attempt', body)
        self.assertIn('return 1', body)

    def test_new_season_trigger_reaches_leaguefixtures_before_second_play(self):
        marker = '# GameMenu -> LeagueFixtures -> patched PlayMatches trigger.'
        self.assertIn(marker, self.text)
        block = self.text.split(marker, 1)[1].split('# Restart/load must reproduce', 1)[0]
        league_wait = "wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures'"
        self.assertIn(league_wait, block)
        self.assertGreaterEqual(block.count('press_play'), 2)
        self.assertLess(block.index(league_wait), block.rindex('press_play'))

    def test_new_season_stock_chain_is_observed_without_manual_message_presses(self):
        marker = '# GameMenu -> LeagueFixtures -> patched PlayMatches trigger.'
        self.assertIn(marker, self.text)
        block = self.text.split(marker, 1)[1].split('# Restart/load must reproduce', 1)[0]
        self.assertNotIn('for step in 1 2 3 4', block)
        self.assertNotIn('press_message_accept', block)
        for token in (
            'CallFunc:[[:space:]]*NewSeasonSetUp1',
            'CallFunc:[[:space:]]*NewSeasonSetUp2',
            'CallFunc:[[:space:]]*NewSeasonSetUp3',
            'CallFunc:[[:space:]]*NewSeasonSetUp4',
            'LoadCareer saveslot:[[:space:]]*0',
            'dump_save post-rollover',
        ):
            self.assertIn(token, block)

    def test_restart_uses_stock_slot0_autoload_instead_of_reopening_save_slot(self):
        marker = '# Restart/load must reproduce the same post-rollover Career state.'
        self.assertIn(marker, self.text)
        block = self.text.split(marker, 1)[1].split('python3 stage4_tools/verify_stage4_season_transition.py', 1)[0]
        self.assertNotIn('open_slot0 reload', block)
        self.assertNotIn('load_existing reload', block)
        self.assertIn("wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 reload-loadcareer", block)
        self.assertIn("wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 reload-gamemenu", block)
        self.assertIn('dump_save post-restart', block)

    def test_stage4_verifier_uses_pre_post_restart_checkpoints(self):
        verifier = (ROOT / 'stage4_tools' / 'verify_stage4_season_transition.py').read_text(encoding='utf-8')
        self.assertIn('usage: verify_stage4_season_transition.py PRE POST RESTART FLOW', verifier)
        self.assertNotIn('PRE SEEDED POST RESTART FLOW', verifier)
        self.assertIn("CallFunc:\\s*NewSeasonSetUp1", verifier)
        self.assertIn("CallFunc:\\s*NewSeasonSetUp4", verifier)
        self.assertIn("competition block rebuilt during season rollover", verifier)

    def test_all_adb_calls_are_bounded_and_last_command_is_recorded(self):
        match = re.search(r'adb\(\)\s*\{(?P<body>.*?)\n\}', self.text, re.S)
        self.assertIsNotNone(match, 'bounded adb wrapper not found')
        body = match.group('body')
        self.assertIn('last-adb-command.txt', body)
        self.assertRegex(body, r'timeout\s+--signal=TERM\s+--kill-after=5s\s+45s')
        self.assertIn('"$ADB_BIN" "$@"', body)

    def test_play_target_uses_measured_api29_pixel4_button_center(self):
        match = re.search(r'press_play\(\)\{\n(?P<body>.*?)\n\}', self.text, re.S)
        self.assertIsNotNone(match, 'press_play function not found')
        body = match.group('body')
        self.assertIn('1080x2280', body)
        self.assertIn('935 1850', body)
        self.assertIn('Stage4 Play target', body)
        self.assertNotIn('press_logical 553 829', body)

if __name__ == '__main__':
    unittest.main()
