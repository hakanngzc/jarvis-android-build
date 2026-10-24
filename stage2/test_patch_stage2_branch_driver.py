import unittest
from pathlib import Path

from patch_stage2_branch_driver import FATAL_ANCHOR, adapt_generated_script, harden_fatal_check
from stage2_checkpoint import FIELD_INDEX

FIXTURE = r'''python3 stage3/patch_stage3_knockout_apk.py "$MODE" "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \
  --evidence "$OUT/STAGE3_KNOCKOUT_APK_PATCH.json" | tee "$OUT/STAGE3_KNOCKOUT_APK_PATCH.txt"
adb install-multiple -r "$SIGNED/base.apk" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true
shot career-gamemenu
lifecycle_background_roundtrip career

# Drive normal stock UI to the next playable match.
echo stage3-tail
'''


class Stage2BranchTransformTest(unittest.TestCase):
    def test_requires_stock_writer_hash_gate(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('verify_stage2_writer_hashes.py', out)
        self.assertIn('STAGE2_WRITER_HASHES.json', out)
        self.assertNotIn('patch_stage3_knockout_apk.py', out)

    def test_runs_real_branch_then_restart_reload(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('--event-type stage2-scenario', out)
        self.assertIn('wait_log \'QUICK SAVE\'', out)
        self.assertIn('reload_saved_career_after_setup', out)
        self.assertIn('--event-type stage2-smoke', out)
        self.assertIn('verify_stage2_branch_runtime.py', out)

    def test_supports_exact_four_scenarios(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('accept|reject|transfer|retirement', out)
        self.assertIn('STAGE2_SCENARIO', out)

    def test_keeps_frida_server_version_pinned(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('FRIDA_VERSION=17.24.3', out)

    def test_dump_save_initializes_tag_before_using_it_under_nounset(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('local tag="$1"\n  local remote=', out)
        self.assertNotIn('local tag="$1" remote=', out)

    def test_records_real_pid_and_diagnostics_before_each_frida_attach(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('require_stage2_pid scenario', out)
        self.assertIn('require_stage2_pid reload', out)
        self.assertIn('stage2-${SCENARIO}-${tag}-no-process.log', out)
        self.assertIn('stage2-${SCENARIO}-${tag}-activity.txt', out)
        self.assertGreaterEqual(out.count('--pid "$STAGE2_PID"'), 2)

    def test_filters_only_appmeasurement_service_anr(self):
        out = harden_fatal_check(FATAL_ANCHOR)
        self.assertIn('AppMeasurementService', out)
        self.assertIn('[ "$anr_count" -eq "$measurement_count" ]', out)
        self.assertIn('runtime-ignored-appmeasurement-anr.txt', out)
        self.assertIn('FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer', out)
        self.assertIn("echo 'NSS-owned crash/ANR detected'", out)

    def test_measurement_only_anr_modal_recovery_uses_wait_and_never_close_app(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('dismiss_measurement_anr_modal', out)
        self.assertIn('runtime-ignored-appmeasurement-anr.txt', out)
        self.assertIn('text="Wait"', out)
        self.assertIn('measurement_anr_wait_dismissed', out)
        self.assertNotIn('text="Close app"', out)
        self.assertNotIn('anr_show_background', out)

    def test_checkpoint_uses_artifact_verified_contract_and_retirement_indices(self):
        self.assertEqual(FIELD_INDEX['lastnegotiations'], 581)
        self.assertEqual(FIELD_INDEX['lasttransferdate'], 582)
        self.assertEqual(FIELD_INDEX['assistbonus'], 898)
        self.assertEqual(FIELD_INDEX['retired'], 910)

    def test_inherited_career_navigation_uses_verified_button_center_and_bounded_retry(self):
        lifecycle = Path('../lifecycle/patch_lifecycle_probe_v3.py').read_text(encoding='utf-8')
        self.assertIn('logical_xy 480 624', lifecycle)
        self.assertNotIn('logical_xy 480 664', lifecycle)
        self.assertIn('for attempt in 1 2 3; do', lifecycle)
        self.assertIn('open_saveslot_from_mainmenu lifecycle-reload-saveslot', lifecycle)

    def test_frida_runner_accepts_numeric_pid(self):
        src = Path('run_frida_script.py').read_text(encoding='utf-8')
        self.assertIn("ap.add_argument('--pid', type=int)", src)
        self.assertIn('device.attach(args.pid if args.pid else args.package)', src)

    def test_frida_runner_compiles_agent_with_java_bridge(self):
        src = Path('run_frida_script.py').read_text(encoding='utf-8')
        self.assertIn('frida.Compiler()', src)
        self.assertIn('compiler.build(', src)
        self.assertIn("project_root=str(project_root)", src)
        scenario = Path('stage2_branch_scenario.js').read_text(encoding='utf-8')
        smoke = Path('frida_smoke.js').read_text(encoding='utf-8')
        self.assertIn("import Java from 'frida-java-bridge';", scenario)
        self.assertIn("import Java from 'frida-java-bridge';", smoke)

    def test_contract_buttons_are_invoked_only_after_stock_screen_setup(self):
        scenario = Path('stage2_branch_scenario.js').read_text(encoding='utf-8')
        setup = 'Contract.m_SetUpScreen(offer, false);'
        self.assertGreaterEqual(scenario.count(setup), 3)
        self.assertLess(scenario.index(setup, scenario.index("SCENARIO === 'accept'")),
                        scenario.index('Contract.m_ButtonAccept(false)', scenario.index("SCENARIO === 'accept'")))
        reject_at = scenario.index("SCENARIO === 'reject'")
        self.assertLess(scenario.index(setup, reject_at), scenario.index('Contract.m_ButtonReject()', reject_at))
        transfer_at = scenario.index("SCENARIO === 'transfer'")
        self.assertLess(scenario.index(setup, transfer_at),
                        scenario.index('Contract.m_ButtonAccept(false)', transfer_at))

    def test_branch_action_is_dispatched_once_from_gl_renderer_thread(self):
        scenario = Path('stage2_branch_scenario.js').read_text(encoding='utf-8')
        self.assertIn("Java.use('com.newstargames.newstarsoccer.BBAndroidGame')", scenario)
        self.assertIn("onDrawFrame.overload('javax.microedition.khronos.opengles.GL10')", scenario)
        self.assertIn('if (!fired)', scenario)
        self.assertIn('executeScenario();', scenario)
        self.assertIn('thread_name:', scenario)
        self.assertIn("const Thread = Java.use('java.lang.Thread');", scenario)
        self.assertIn('Thread.currentThread().getName().toString()', scenario)

    def test_runtime_verifier_requires_gl_renderer_thread_evidence(self):
        verifier = Path('verify_stage2_branch_runtime.py').read_text(encoding='utf-8')
        self.assertIn("scenario.get('thread_name', '').startswith('GLThread')", verifier)
        self.assertIn('scenario executed on GL renderer thread', verifier)

    def test_removes_old_stage3_tail_before_exit(self):
        out = adapt_generated_script(FIXTURE)
        self.assertNotIn('echo stage3-tail', out.split('exit 0', 1)[0])


if __name__ == '__main__':
    unittest.main()
