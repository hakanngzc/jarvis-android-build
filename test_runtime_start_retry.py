import importlib.util
import unittest
from pathlib import Path


def load(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class RuntimeStartRetryTests(unittest.TestCase):
    def test_prepared_gate_gets_two_bounded_process_start_attempts(self):
        base = load('stage2_residual_tools/prepare_stage2_gate.py', 'prepare_stage2_gate_start_test')
        retry = load('stage2_residual_tools/prepare_runtime_start_retry.py', 'prepare_runtime_start_retry')
        prepared = base.prepare_text(Path('stage2_residual_gate.sh').read_text(encoding='utf-8'))
        hardened = retry.harden(prepared)
        self.assertIn('start_game $tag attempt $start_attempt/2', hardened)
        self.assertIn('for start_attempt in 1 2', hardened)
        self.assertIn('${tag}-mainmenu-attempt-${start_attempt}-timeout.txt', hardened)
        self.assertIn('controlled process restart', hardened)
        self.assertIn('failed after 2 controlled attempts', hardened)
        self.assertIn('fatal_check || return 1', hardened)


if __name__ == '__main__':
    unittest.main()
