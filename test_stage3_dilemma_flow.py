#!/usr/bin/env python3
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


if __name__ == "__main__":
    unittest.main()
