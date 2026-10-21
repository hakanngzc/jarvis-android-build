#!/usr/bin/env python3
import unittest
from pathlib import Path


class Stage3AdOverlayFlowTest(unittest.TestCase):
    def test_post_match_state_machine_dismisses_ad_with_back(self):
        patch = Path("stage3_match_flow_patch.py").read_text(encoding="utf-8")
        self.assertIn(" ad ", patch, "post-match wait/state set must include ad")
        self.assertIn("ad)", patch, "post-match state machine must handle ad")
        self.assertIn("input keyevent 4", patch, "ad handler must dismiss the interstitial with Android Back")


if __name__ == "__main__":
    unittest.main()
