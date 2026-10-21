#!/usr/bin/env python3
import unittest
from pathlib import Path


class Stage3ReadinessRenderGateTest(unittest.TestCase):
    def test_readiness_requires_a_real_screenshot_frame(self):
        patch = Path("stage3_readiness_patch.py").read_text(encoding="utf-8")
        self.assertIn("screencap -p", patch, "readiness must sample the rendered frame")
        self.assertIn("30000", patch, "readiness must reject tiny blank screenshots")
        self.assertIn("render-ready.png", patch, "successful rendered-frame evidence must be preserved")


if __name__ == "__main__":
    unittest.main()
