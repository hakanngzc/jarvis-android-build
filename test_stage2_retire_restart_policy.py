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


class Stage2RetireRestartPolicyTests(unittest.TestCase):
    def test_retirement_uses_stock_mainmenu_reload_boundary(self):
        base = load('stage2_residual_tools/prepare_stage2_gate.py', 'retire_restart_base')
        stable = load('stage2_residual_tools/prepare_stage2_gamemenu_stable.py', 'retire_restart_stable')
        retire = load('stage2_residual_tools/prepare_stage2_retire_restart.py', 'retire_restart_policy')
        text = base.prepare_text(Path('stage2_residual_gate.sh').read_text(encoding='utf-8'))
        text = stable.harden(text)
        hardened = retire.harden(text)

        self.assertIn('retire-post-restart-mainmenu.log', hardened)
        self.assertIn("capture_log 'retire post-restart stock MainMenu retired-slot boundary'", hardened)
        self.assertIn('shot retire-post-restart-mainmenu', hardened)
        self.assertIn('dump_save "$scenario-post-restart"; checkpoint "$scenario-post-restart"', hardened)
        self.assertIn('--retire-mainmenu-proof "$OUT/retire-post-restart-mainmenu.log"', hardened)
        self.assertNotIn('--second-after-reload', hardened)
        self.assertNotIn('retire second stock retirement writer no-op', hardened)

    def test_nonretired_branches_keep_real_loadcareer_path(self):
        text = Path('stage2_residual_tools/prepare_stage2_retire_restart.py').read_text(encoding='utf-8')
        self.assertIn('open_slot0 "$scenario-restart"', text)
        self.assertIn('load_existing "$scenario-restart"', text)
        self.assertIn('Do not manufacture a non-player LoadCareer path', text)


if __name__ == '__main__':
    unittest.main()
