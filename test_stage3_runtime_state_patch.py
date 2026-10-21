import importlib.util
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
MODULE = ROOT / 'stage3_runtime_state_patch.py'

SOURCE = r'''#!/usr/bin/env bash
set -euo pipefail
PKG=com.newstargames.newstarsoccer
OUT="$RUNNER_TEMP/stage3-minimal"
WORK="$RUNNER_TEMP/stage3-work"
FLOW="$OUT/STAGE3_RUNTIME_FLOW.log"
press_message_accept(){ :; }
press_play(){ :; }
current_state(){
  adb logcat -d -v brief > "$WORK/state.log" 2>/dev/null || true
  # MatchReview has an internal weekly-report phase that does not emit a new SetActive/Create Screen line.
  # Stock 4.31 logs this phase through matchReviewBuxAwarded immediately before the weekly summary is shown.
  if grep -q 'USE player.matchReviewBuxAwarded:' "$WORK/state.log"; then
    echo matchreview
    return
  fi
  local line; line="$(grep -Ei 'SETTING ACTIVE:|SetActive:|Create Screen:' "$WORK/state.log" | tail -1 || true)"
  case "${line,,}" in
    *matchstats*) echo matchstats;; *matchreview*) echo matchreview;; *leaguefixtures*) echo leaguefixtures;; *gamemenu*) echo gamemenu;; *message*) echo message;;
    *" active: match"*|*"setactive: match"*|*"screen: match"*) echo match;;
    *" active: league"*|*"setactive: league"*|*"screen: league"*) echo league;; *) echo unknown;;
  esac
}
wait_state(){
  local wanted="$1" timeout_s="${2:-30}" i state
  for i in $(seq 0 "$timeout_s"); do fatal_check || return 1; state="$(current_state)"; if [[ " $wanted " == *" $state "* ]]; then echo "$state"; return 0; fi; sleep 1; done
  capture_log "timeout state $wanted"; echo unknown; return 1
}
for step in $(seq 1 16); do
  [ "$state" = gamemenu ] && break
  case "$state" in
    leaguefixtures|league|matchreview)
      clear_log
      press_play 3
      ;;
    message)
      clear_log
      press_message_accept 3
      ;;
    *) sleep 2 ;;
  esac
  state="$(wait_state 'league matchreview gamemenu message leaguefixtures ad' 25 || true)"
done
'''


class RuntimeStatePatchTests(unittest.TestCase):
    def load(self):
        self.assertTrue(MODULE.exists(), 'stage3_runtime_state_patch.py must exist')
        spec = importlib.util.spec_from_file_location('stage3_runtime_state_patch', MODULE)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_hardens_post_patch_runtime_state_machine(self):
        mod = self.load()
        hardened = mod.harden(SOURCE)
        self.assertIn('python3 stage3_harness.py state', hardened)
        self.assertNotIn("echo matchreview\n    return", hardened)
        self.assertIn('weeklyreport', hardened)
        self.assertIn('capture_stage3_diagnostics', hardened)
        self.assertIn('LAST_INPUT=', hardened)
        self.assertIn('failure_layer=', hardened)
        with tempfile.NamedTemporaryFile('w', suffix='.sh', delete=False) as f:
            f.write(hardened)
            path = f.name
        proc = subprocess.run(['bash', '-n', path], text=True, capture_output=True)
        pathlib.Path(path).unlink(missing_ok=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_double_patch_is_rejected(self):
        mod = self.load()
        hardened = mod.harden(SOURCE)
        with self.assertRaises(ValueError):
            mod.harden(hardened)


if __name__ == '__main__':
    unittest.main()
