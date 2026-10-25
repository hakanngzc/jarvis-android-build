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


class Stage4LivePacingTests(unittest.TestCase):
    def test_live_driver_uses_bounded_configurable_settle_delay(self):
        mod = load_module('stage4_tools/prepare_stage4_live_input.py', 'prepare_stage4_live_input_pacing')
        driver = mod.DRIVER
        self.assertIn('LIVE_INPUT_SETTLE_SECONDS', driver)
        self.assertIn('sleep "${LIVE_INPUT_SETTLE_SECONDS:-1}"', driver)
        self.assertNotIn('sleep 3\n    return 0', driver)
        self.assertNotIn('m_Simulate', driver)
        self.assertNotIn('m_skipMatches', driver)


if __name__ == '__main__':
    unittest.main()
