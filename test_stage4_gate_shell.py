#!/usr/bin/env python3
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

class Stage4GateShellRegressionTests(unittest.TestCase):
    def test_dump_save_does_not_expand_tag_in_same_local_statement(self):
        text = (ROOT / 'stage4_season_gate.sh').read_text(encoding='utf-8')
        match = re.search(r'dump_save\(\)\{\n(?P<body>.*?)\n\}', text, re.S)
        self.assertIsNotNone(match, 'dump_save function not found')
        body = match.group('body')
        self.assertNotRegex(
            body,
            r'local\s+tag="\$1"[^\n]*\$\{tag\}',
            'set -u regression: tag is expanded in the same local statement that assigns it',
        )

if __name__ == '__main__':
    unittest.main()
