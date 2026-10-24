import unittest
from pathlib import Path

from patch_stage2_branch_driver import adapt_generated_script

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

    def test_removes_old_stage3_tail_before_exit(self):
        out = adapt_generated_script(FIXTURE)
        self.assertNotIn('echo stage3-tail', out.split('exit 0', 1)[0])


if __name__ == '__main__':
    unittest.main()
