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

if __name__ == '__main__':
    unittest.main()
