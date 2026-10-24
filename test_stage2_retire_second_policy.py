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


class Stage2RetireSecondPolicyTests(unittest.TestCase):
    def test_hardener_requires_stock_play_hits_for_second_retirement_writer(self):
        p = Path('stage2_residual_tools/prepare_stage2_retire_second.py')
        self.assertTrue(p.exists(), 'retirement reload hardener must exist')
        module = load_module(str(p), 'prepare_stage2_retire_second')
        text = Path('stage2_residual_gate.sh').read_text(encoding='utf-8')
        hardened = module.harden(text)
        self.assertIn('retire second GameMenu Play attempt $second_gm_attempt/3', hardened)
        self.assertIn('HitGadget: gamemenu.btn_Play', hardened)
        self.assertIn('retire second LeagueFixtures Play attempt $second_lf_attempt/3', hardened)
        self.assertIn('HitGadget: leaguefixtures.btn_Play', hardened)
        self.assertIn("capture_log 'retire second stock retirement writer no-op'", hardened)

    def test_workflow_applies_retirement_reload_hardener(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        self.assertIn('prepare_stage2_retire_second.py', text)
        self.assertIn('stage2-residual-gate.retire.sh', text)
        self.assertIn('bash "$RUNNER_TEMP/stage2-residual-gate.retire.sh"', text)


if __name__ == '__main__':
    unittest.main()
