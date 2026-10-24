import importlib.util
import unittest
from pathlib import Path


def load_preparer():
    path = Path('stage2_residual_tools/prepare_stage2_gate.py')
    spec = importlib.util.spec_from_file_location('prepare_stage2_gate', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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

    def test_gate_preparer_distinguishes_gms_measurement_anr(self):
        p = Path('stage2_residual_tools/prepare_stage2_gate.py')
        text = p.read_text(encoding='utf-8')
        self.assertIn('AppMeasurementService', text, 'known GMS-free measurement-service ANR must be classified explicitly')
        self.assertIn('ignored-gms-measurement-anr.txt', text, 'ignored measurement ANR must remain preserved as evidence')
        self.assertIn('NSS-owned ANR detected', text, 'all other package ANRs must still fail the runtime gate')
        self.assertIn('runtime-fatal-logcat.txt', text, 'real crash/ANR evidence must still be preserved')

    def test_both_gates_use_durable_save_then_restart_instead_of_news_settlement(self):
        for gate in ('stage2_residual_gate.sh', 'stage4_natural_season_gate.sh'):
            with self.subTest(gate=gate):
                text = Path(gate).read_text(encoding='utf-8')
                self.assertIn('Fresh Career save evidence missing', text)
                self.assertIn('bootstrap-restart', text)
                self.assertIn('SAVE CAREER', text)
                self.assertNotIn('settle_bootstrap_to_gamemenu', text)

    def test_gate_preparer_accepts_both_residual_gate_sources(self):
        preparer = load_preparer()
        for gate in ('stage2_residual_gate.sh', 'stage4_natural_season_gate.sh'):
            with self.subTest(gate=gate):
                source = Path(gate).read_text(encoding='utf-8')
                prepared = preparer.prepare_text(source)
                self.assertIn('render-probe.png', prepared)
                self.assertIn('tap 795 1399', prepared)
                self.assertIn('tap 935 1850', prepared)
                self.assertIn('Fresh Career save evidence missing', prepared)
                self.assertNotIn('settle_bootstrap_to_gamemenu', prepared)


if __name__ == '__main__':
    unittest.main()
