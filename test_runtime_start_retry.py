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

    def test_startup_crash_is_stashed_and_retried_instead_of_aborting_first_attempt(self):
        base = load('stage2_residual_tools/prepare_stage2_gate.py', 'prepare_stage2_gate_start_crash_test')
        retry = load('stage2_residual_tools/prepare_runtime_start_retry.py', 'prepare_runtime_start_retry_crash')
        prepared = base.prepare_text(Path('stage2_residual_gate.sh').read_text(encoding='utf-8'))
        hardened = retry.harden(prepared)

        # Run #294 proves the stock app can hit a disposable 16 MB AtlasManager
        # OOM before MainMenu on one emulator start. The helper advertises two
        # bounded starts, so a first-attempt startup crash must be preserved as
        # setup evidence and retried, not abort the whole natural-season run.
        self.assertIn('stash_startup_fatal(){', hardened)
        self.assertIn('${tag}-startup-attempt-${start_attempt}-fatal.txt', hardened)
        self.assertIn('start_game $tag attempt $start_attempt crashed before stable MainMenu; controlled process restart', hardened)
        self.assertIn('startup_crashed=1', hardened)
        self.assertIn('if ! fatal_check; then', hardened)
        self.assertIn('continue', hardened)
        self.assertNotIn('fatal_check || return 1\n      echo "start_game $tag attempt $start_attempt did not reach Monkey MainMenu', hardened)
        self.assertNotIn('fatal_check || return 1\n    echo "start_game $tag attempt $start_attempt reached MainMenu log but not a stable rendered process', hardened)

    def test_stage4_setup_retry_cleans_disposable_workdir_before_each_attempt(self):
        runner = Path('stage4_tools/run_stage4_natural_gate.sh').read_text(encoding='utf-8')

        # Run #286 attempt 2 reused the previous xapk extraction directory and
        # blocked for hours on unzip's interactive "replace ...?" prompt. Every
        # setup attempt must begin with a fresh disposable work directory while
        # retaining the evidence output directory from earlier failed attempts.
        cleanup = 'rm -rf "${RUNNER_TEMP:?}/stage4-natural-work"'
        self.assertIn(cleanup, runner)
        self.assertIn('for setup_attempt in 1 2 3', runner)
        self.assertLess(runner.index(cleanup), runner.index('bash "$GATE"'))
        self.assertNotIn('rm -rf "${RUNNER_TEMP:?}/stage4-natural"\n', runner)


if __name__ == '__main__':
    unittest.main()
