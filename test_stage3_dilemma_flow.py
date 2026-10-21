#!/usr/bin/env python3
import re
import unittest
from pathlib import Path


class Stage3DilemmaFlowTest(unittest.TestCase):
    def test_post_match_state_machine_handles_stock_dilemma_option(self):
        patch = Path("stage3_match_flow_patch.py").read_text(encoding="utf-8")
        self.assertIn(" dilemma ", patch, "post-match wait/state sets must include dilemma")
        self.assertIn("dilemma)", patch, "post-match state machine must handle dilemma")
        self.assertIn(
            "press_logical 320 400",
            patch,
            "dilemma handler must press inside verified TopOption stock rectangle",
        )

    def test_dilemma_retry_does_not_clear_parent_screen_log(self):
        patch = Path("stage3_match_flow_patch.py").read_text(encoding="utf-8")
        m = re.search(r"dilemma\)\n(.*?)\n\s*;;", patch, re.S)
        self.assertIsNotNone(m, "dilemma handler not found")
        handler = m.group(1)
        self.assertNotIn(
            "clear_log",
            handler,
            "dilemma retry must preserve parent screen evidence while splashmessage consumes the first tap",
        )
        self.assertIn("press_logical 320 400", handler)


if __name__ == "__main__":
    unittest.main()
