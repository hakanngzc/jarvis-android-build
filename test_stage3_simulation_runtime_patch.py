#!/usr/bin/env python3
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
PATCHER = ROOT / 'stage3_simulation_runtime_patch.py'


class Stage3SimulationRuntimePatchTests(unittest.TestCase):
    def load_module(self):
        spec = importlib.util.spec_from_file_location('stage3_simulation_runtime_patch', PATCHER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def fixture(self):
        return '''#!/usr/bin/env bash
PYTHONPATH="$PWD/stage3_tools" python3 stage3_tools/patch_stage3_fast_match_probe.py "$WORK/base-career-unsigned.apk" "$WORK/base-stage3-unsigned.apk" | tee "$OUT/stage3-fast-match-patch.txt"
# First-time Career match can show a tutorial overlay that consumes the first
MATCHSTATS_REACHED=0
press_play 3
shot stage3-matchstats
# later stock post-match flow remains intact
python3 stage3_tools/verify_stage3_minimal.py "$OUT/pre-match-MonkeyGame.xml" "$OUT/post-match-MonkeyGame.xml" "$OUT/post-restart-MonkeyGame.xml" "$FLOW" | tee "$OUT/STAGE3_FULL_GATE.txt"
grep -q 'STAGE3_FULL_GATE_PASS' "$OUT/STAGE3_FULL_GATE.txt"
echo 'STAGE3_MINIMAL_FULL_RUNTIME_PASS'\n'''

    def test_transform_uses_stock_neutral_gadget_and_simulation_verifier(self):
        mod = self.load_module()
        out = mod.transform(self.fixture())
        self.assertIn('patch_debug_enabled_test.py', out)
        self.assertNotIn('patch_stage3_fast_match_probe.py', out)
        self.assertIn('press_logical 361 53', out)
        self.assertIn('match\\.autoplayAverage', out)
        self.assertIn('SIMULATING MATCH', out)
        self.assertIn('verify_stage3_simulation.py', out)
        self.assertIn('STAGE3_SIMULATION_GATE_PASS', out)
        self.assertIn('# later stock post-match flow remains intact', out)

    def test_transform_refuses_unhardened_match_flow(self):
        mod = self.load_module()
        bad = self.fixture().replace('# First-time Career match can show a tutorial overlay that consumes the first\n', '# no hardened anchor\n')
        with self.assertRaises(ValueError):
            mod.transform(bad)


if __name__ == '__main__':
    unittest.main()
