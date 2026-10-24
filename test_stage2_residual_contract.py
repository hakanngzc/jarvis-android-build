import importlib.util
import unittest
from pathlib import Path

from stage3_tools.stage2_checkpoint import FIELD_INDEX, extract_checkpoint


def load_module(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def prepare_gate(path: Path) -> str:
    preparer = load_module('stage2_residual_tools/prepare_stage2_gate.py', 'prepare_stage2_gate')
    visual = load_module('stage2_residual_tools/prepare_chooseclub_visual.py', 'prepare_chooseclub_visual')
    return visual.harden_chooseclub(preparer.prepare_text(path.read_text(encoding='utf-8')))


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

    def test_checkpoint_contract_markers_account_for_fixed_serialization_loops(self):
        # NSS 4.31 p_GetPlayerData has two fixed loops before these markers:
        # 10 * (items, vehicles, properties) and
        # 100 * (technique, pace, vision, setpieces, power).
        # Their runtime CSV positions are therefore 59/60 + 522 = 581/582.
        self.assertEqual(FIELD_INDEX['lastnegotiations'], 581)
        self.assertEqual(FIELD_INDEX['lasttransferdate'], 582)

        tokens = ['0'] * 583
        tokens[0] = '12'
        tokens[1] = '62'
        tokens[2] = '4336'
        tokens[3] = 'The Kid'
        tokens[4] = 'Kid'
        tokens[13] = '0'
        tokens[33] = '1'
        tokens[34] = '1'
        tokens[581] = '12'
        tokens[582] = '12'
        state = 'global;' + ','.join(tokens) + ';club;competition;additional'
        cp = extract_checkpoint(state, 0)
        self.assertEqual(cp['lastnegotiations'], 12)
        self.assertEqual(cp['lasttransferdate'], 12)

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

    def test_retirement_second_probe_reaches_authoritative_writer_after_reload(self):
        text = Path('stage2_residual_gate.sh').read_text(encoding='utf-8')
        self.assertIn('retire-second-leaguefixtures', text)
        self.assertIn("capture_log 'retire second probe GameMenu -> LeagueFixtures'", text)
        self.assertIn("capture_log 'retire second stock retirement writer no-op'", text)

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

    def test_visual_helper_is_nounset_safe_and_requires_stock_input_evidence(self):
        text = Path('stage2_residual_tools/prepare_chooseclub_visual.py').read_text(encoding='utf-8')
        self.assertNotIn('local tag="$1" x="$2" y="$3" before=', text,
                         'dependent evidence paths must not read tag in the same local command')
        self.assertIn('local tag="$1" x="$2" y="$3"', text)
        self.assertIn('HitGadget: (message|chooseclub)\\.btn_Ok', text)
        self.assertIn('setup control did not register', text)
        self.assertNotIn('cmp -s "$before" "$after"', text,
                         'ticker/animation pixel changes are not proof that the setup control registered')

    def test_prepared_open_slot_scope_is_nounset_safe(self):
        for gate in ('stage2_residual_gate.sh', 'stage4_natural_season_gate.sh'):
            with self.subTest(gate=gate):
                prepared = prepare_gate(Path(gate))
                self.assertIn('local tag attempt reached slot_attempt slot_hit', prepared)
                self.assertIn('tag="${1-}"', prepared)
                self.assertIn('reached=0', prepared)
                self.assertIn('slot_hit=0', prepared)
                self.assertIn('"$WORK/${tag}-slot0-attempt-${slot_attempt}.txt"', prepared)
                self.assertNotIn('local tag="$1" attempt reached=0', prepared)

    def test_prepared_gates_use_durable_save_then_restart_not_news_settlement(self):
        for gate in ('stage2_residual_gate.sh', 'stage4_natural_season_gate.sh'):
            with self.subTest(gate=gate):
                prepared = prepare_gate(Path(gate))
                self.assertIn('Fresh Career save evidence missing', prepared)
                self.assertIn('bootstrap-restart', prepared)
                self.assertIn('SAVE CAREER', prepared)
                self.assertNotIn('settle_bootstrap_to_gamemenu', prepared)

    def test_prepared_gates_use_stock_hit_proven_chooseclub_progression(self):
        for gate in ('stage2_residual_gate.sh', 'stage4_natural_season_gate.sh'):
            with self.subTest(gate=gate):
                prepared = prepare_gate(Path(gate))
                self.assertIn('press_and_require_stock_hit', prepared)
                self.assertIn('fresh-setup-ok-$n', prepared)
                self.assertIn('HitGadget: (message|chooseclub)\\.btn_Ok', prepared)
                self.assertIn('Create Screen:[[:space:]]*choosenation', prepared)
                self.assertNotIn('cmp -s "$before" "$after"', prepared)

    def test_gate_preparer_accepts_both_residual_gate_sources(self):
        for gate in ('stage2_residual_gate.sh', 'stage4_natural_season_gate.sh'):
            with self.subTest(gate=gate):
                prepared = prepare_gate(Path(gate))
                self.assertIn('render-probe.png', prepared)
                self.assertIn('tap 795 1399', prepared)
                self.assertIn('tap 935 1850', prepared)
                self.assertIn('Fresh Career save evidence missing', prepared)


if __name__ == '__main__':
    unittest.main()
