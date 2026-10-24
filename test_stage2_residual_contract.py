import unittest
from pathlib import Path


class Stage2ResidualContractTests(unittest.TestCase):
    def test_probe_exists_and_uses_stock_writers(self):
        p = Path('stage2_residual_tools/patch_stage2_residual_probe.py')
        self.assertTrue(p.exists(), 'residual probe patcher must exist')
        text = p.read_text(encoding='utf-8')
        for required in (
            'm_GetOffer',
            'm_ButtonAccept',
            'm_ButtonReject',
            'p_SignContract',
            'm_SelectById',
            'c_TScreen_Retirement',
            'm_ButtonPlay',
            'g_GSPlayerPlayMatches',
        ):
            self.assertIn(required, text)
        for forbidden in (
            "->m_clubid:I",
            "->m_retired:I",
            "->m_lasttransferdate:I",
            "->m_lastnegotiations:I",
        ):
            self.assertNotIn(forbidden, text, f'probe must not directly write durable field {forbidden}')

    def test_runtime_gate_requires_restart_reload_for_every_branch(self):
        p = Path('stage2_residual_gate.sh')
        self.assertTrue(p.exists(), 'residual Android runtime gate must exist')
        text = p.read_text(encoding='utf-8')
        for scenario in ('accept', 'reject', 'transfer', 'retire'):
            self.assertIn(f'run_scenario {scenario}', text)
        self.assertIn('start_game "$scenario-restart"', text)
        self.assertIn('dump_save "$scenario-post-restart"', text)
        self.assertIn('--restart "$OUT/$scenario-post-restart.json"', text)
        self.assertIn('LoadCareer saveslot: 0', text)
        self.assertIn('STAGE2_RESIDUAL_RUNTIME_PASS', text)

    def test_gate_preparer_hardens_real_pixel4_bootstrap(self):
        p = Path('stage2_residual_tools/prepare_stage2_gate.py')
        self.assertTrue(p.exists(), 'runtime gate preparer must exist')
        text = p.read_text(encoding='utf-8')
        self.assertIn("(2|3)", text, 'Play helper must support both Stage2 and Stage4 delay variants')
        self.assertIn('render-probe.png', text, 'MainMenu log alone is not enough; require rendered frame readiness')
        self.assertIn('HitGadget: saveslot.btn_Slot0', text, 'Slot0 input must be proven by stock gadget evidence')
        self.assertIn('Career press attempt', text, 'Career input must use bounded controlled retries')
        self.assertIn('patch_first_run_overlays.py', text, 'Stage2 bootstrap must remove only first-run overlays before UI input')
        self.assertIn('tap 795 1399', text, 'use the proven API29 Pixel4 Career target')
        self.assertIn('tap 935 1850', text, 'use the proven API29 Pixel4 Play target')


if __name__ == '__main__':
    unittest.main()
