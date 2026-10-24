import unittest
from pathlib import Path

from patch_stage2_frida_smoke_driver import adapt_generated_script

FIXTURE = r'''python3 stage3/patch_stage3_knockout_apk.py "$MODE" "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk" \
  --evidence "$OUT/STAGE3_KNOCKOUT_APK_PATCH.json" | tee "$OUT/STAGE3_KNOCKOUT_APK_PATCH.txt"
adb install-multiple -r "$SIGNED/base.apk" "$SIGNED/config.tr.apk" "$SIGNED/config.xxhdpi.apk" >/dev/null
adb shell pm clear "$PKG" >/dev/null || true
shot career-gamemenu
lifecycle_background_roundtrip career

# Drive normal stock UI to the next playable match.
echo stage3-tail
'''


class Stage2FridaSmokeTransformTest(unittest.TestCase):
    def test_removes_unrelated_stage3_patch(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('cp "$WORK/base-career-probe.apk" "$WORK/base-knockout-probe.apk"', out)
        self.assertNotIn('patch_stage3_knockout_apk.py', out)

    def test_installs_matching_frida_server_before_app(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('FRIDA_VERSION=17.24.3', out)
        self.assertIn('frida-server-${FRIDA_VERSION}-android-x86_64.xz', out)
        self.assertLess(out.index('frida-server-${FRIDA_VERSION}-android-x86_64.xz'), out.index('adb install-multiple'))

    def test_stops_after_stock_career_smoke(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('stage2/run_frida_script.py', out)
        self.assertIn('VERDICT=STAGE2_FRIDA_SMOKE_PASS', out)
        self.assertNotIn('echo stage3-tail', out.split('exit 0', 1)[0])

    def test_smoke_agent_uses_compiled_frida17_java_bridge(self):
        agent = Path('frida_smoke.js').read_text(encoding='utf-8')
        runner = Path('run_frida_script.py').read_text(encoding='utf-8')
        self.assertIn("import Java from 'frida-java-bridge';", agent)
        self.assertIn('frida.Compiler()', runner)
        self.assertIn('compiler.build(', runner)
        self.assertIn('session.create_script(bundle)', runner)

    def test_smoke_attach_uses_verified_numeric_pid(self):
        out = adapt_generated_script(FIXTURE)
        self.assertIn('STAGE2_SMOKE_PID="$(pid_one)"', out)
        self.assertIn('test -n "$STAGE2_SMOKE_PID"', out)
        self.assertIn('--pid "$STAGE2_SMOKE_PID"', out)
        self.assertIn('stage2-smoke-no-process.log', out)

    def test_refuses_changed_install_shape(self):
        with self.assertRaises(ValueError):
            adapt_generated_script(FIXTURE.replace('adb install-multiple -r', 'adb install-multiple --changed -r'))


if __name__ == '__main__':
    unittest.main()
