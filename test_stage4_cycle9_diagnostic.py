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


class Stage4Cycle9DiagnosticTests(unittest.TestCase):
    def test_cycle9_diagnostic_seeds_real_natural_save_without_claiming_final_pass(self):
        p = Path('stage4_tools/prepare_stage4_cycle9_diagnostic.py')
        self.assertTrue(p.exists(), 'diagnostic preparer must exist')
        module = load_module(str(p), 'prepare_stage4_cycle9_diagnostic')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)

        self.assertIn('STAGE4_DIAGNOSTIC_ARTIFACT_ID', prepared)
        self.assertIn('cycle-9-MonkeyGame.xml', prepared)
        self.assertIn('actions/artifacts/${STAGE4_DIAGNOSTIC_ARTIFACT_ID}/zip', prepared)
        self.assertIn('Authorization: Bearer ${GH_TOKEN}', prepared)
        self.assertIn('diagnostic cycle9 seed loaded', prepared)
        self.assertIn('checkpoint natural-baseline', prepared)
        self.assertIn('STAGE4_DIAGNOSTIC_BASELINE=cycle9', prepared)
        self.assertEqual(prepared.count('dump_save natural-baseline; checkpoint natural-baseline'), 1)

        # Proven post-season restart behavior can publish MainMenu before slot0
        # finishes auto-loading. Do not immediately press Career/SaveSlot on the
        # first MainMenu marker; give the bounded auto-load window a chance first.
        self.assertIn('seed_mainmenu=1\n  fi\n  sleep 1', prepared)
        self.assertNotIn('seed_mainmenu=1\n    break', prepared)

        # Diagnostic continuation may discover blockers, but must never masquerade
        # as the final from-fresh natural-season proof.
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_diagnostic_workflow_isolated_from_canonical_branch_and_cannot_pass_final_verifier(self):
        text = Path('.github/workflows/nss-stage4-cycle9-diagnostic.yml').read_text(encoding='utf-8')
        self.assertIn('nss-stage4-diagnostic-cycle9-20261026', text)
        self.assertNotIn('branches: [nss-residual-runtime-20261024]', text)
        self.assertIn('actions: read', text)
        self.assertIn("STAGE4_DIAGNOSTIC_ARTIFACT_ID: '12647883054'", text)
        self.assertIn("MIN_PROGRESS_DAYS: '9999'", text)
        self.assertIn("MIN_MATCH_CYCLES: '999'", text)
        self.assertIn("MIN_WALL_SECONDS: '999999'", text)
        self.assertIn('prepare_stage4_cycle9_diagnostic.py', text)
        self.assertIn('stage4-cycle9-diagnostic-evidence-${{ github.run_attempt }}', text)


if __name__ == '__main__':
    unittest.main()
