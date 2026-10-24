import unittest

from patch_lifecycle_probe_v2 import harden_generated_script

FIXTURE = r'''pid_one(){ adb shell pidof "$PKG" 2>/dev/null | tr -d '\r' | awk '{print $1}'; }
lifecycle_background_roundtrip(){
  local tag="$1" before hidden after
  before="$(pid_one)"; [ -n "$before" ] || { echo "missing PID before background ($tag)"; return 1; }
  adb shell input keyevent 3 >/dev/null 2>&1 || true
  sleep 3
  hidden="$(pid_one)"; [ "$before" = "$hidden" ] || { echo "process died in background ($tag): $before -> $hidden"; return 1; }
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  sleep 3
  after="$(pid_one)"; [ "$before" = "$after" ] || { echo "process changed after foreground ($tag): $before -> $after"; return 1; }
}
'''


class LifecyclePatchV2Test(unittest.TestCase):
    def test_pid_lookup_cannot_trip_errexit(self):
        out = harden_generated_script(FIXTURE)
        self.assertIn('(adb shell pidof "$PKG" 2>/dev/null || true)', out)

    def test_background_pid_loss_writes_diagnostics(self):
        out = harden_generated_script(FIXTURE)
        self.assertIn('lifecycle-${tag}-background-processes.txt', out)
        self.assertIn('lifecycle-${tag}-background-logcat.txt', out)
        self.assertIn('"${tag}_background_process_survived" FAIL', out)

    def test_foreground_pid_change_writes_diagnostics(self):
        out = harden_generated_script(FIXTURE)
        self.assertIn('lifecycle-${tag}-foreground-processes.txt', out)
        self.assertIn('lifecycle-${tag}-foreground-logcat.txt', out)
        self.assertIn('"${tag}_foreground_same_pid" FAIL', out)

    def test_refuses_unknown_generated_shape(self):
        with self.assertRaises(ValueError):
            harden_generated_script(FIXTURE.replace('process died in background', 'changed diagnostic'))


if __name__ == '__main__':
    unittest.main()
