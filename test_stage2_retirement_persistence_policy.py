import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).parent


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


FIXTURE = '''
build_probe accept
build_probe reject
build_probe transfer "$DEST_CLUB"
build_probe retire

run_scenario(){
  local scenario="$1" dest="${2:-}"
  start_game "$scenario-restart"
  open_slot0 "$scenario-restart"

  if [ "$scenario" = retire ]; then
    # A retired slot may remain on SaveSlot instead of entering GameMenu. Opening
    # SaveSlot is still the stock runtime metadata reload boundary; raw Career
    # state is then checked and a second stock ButtonPlay no-op is attempted only
    # if LoadCareer remains available.
    sleep 3; capture_log 'retire post-restart SaveSlot metadata'; shot retire-post-restart-saveslot
    adb logcat -d -v brief > "$WORK/retire-restart-state.txt" 2>/dev/null || true
    if grep -q 'LoadCareer saveslot: 0' "$WORK/retire-restart-state.txt"; then
      wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 30 retire-reload-gamemenu || true
    fi
  else
    load_existing "$scenario-restart"
  fi
  dump_save "$scenario-post-restart"; checkpoint "$scenario-post-restart"

  extra=()
  if [ "$scenario" = transfer ]; then extra+=(--destination-club-id "$dest"); fi
  if [ "$scenario" = retire ]; then
    # If runtime still allows the retired Career to be loaded, invoke the exact
    # patched PlayMatches trigger again. GameMenu Play first opens LeagueFixtures;
    # the second Play reaches the authoritative stock Retirement.m_ButtonPlay.
    # Because m_retired was restored nonzero, the second writer execution must
    # leave the durable Career checkpoint unchanged.
    if grep -q 'LoadCareer saveslot: 0' "$WORK/retire-restart-state.txt"; then
      clear_log
      press_play 3
      wait_log 'Create Screen:[[:space:]]*leaguefixtures|SETTING ACTIVE:[[:space:]]*leaguefixtures|SetActive:[[:space:]]*leaguefixtures' 30 retire-second-leaguefixtures
      fatal_check
      capture_log 'retire second probe GameMenu -> LeagueFixtures'
      clear_log
      press_play 3
      sleep 3
      fatal_check
      capture_log 'retire second stock retirement writer no-op'
      dump_save retire-second-after-reload
      checkpoint retire-second-after-reload
    else
      cp "$OUT/retire-post-restart.json" "$OUT/retire-second-after-reload.json"
    fi
    extra+=(--second-after-reload "$OUT/retire-second-after-reload.json")
  fi

  python3 stage2_residual_tools/verify_stage2_residual.py \\
    --scenario "$scenario" --base "$OUT/baseline.json" \\
    --post "$OUT/$scenario-post.json" --restart "$OUT/$scenario-post-restart.json" \\
    "${extra[@]}" --out "$OUT/$scenario-verdict.json" | tee "$OUT/$scenario-verdict.txt"
}

run_scenario accept
run_scenario reject
run_scenario transfer "$DEST_CLUB"
run_scenario retire

grep -q 'STAGE2_ACCEPT_RESTART_RELOAD_PASS' "$OUT/accept-verdict.txt"
grep -q 'STAGE2_REJECT_RESTART_RELOAD_PASS' "$OUT/reject-verdict.txt"
grep -q 'STAGE2_TRANSFER_RESTART_RELOAD_PASS' "$OUT/transfer-verdict.txt"
grep -q 'STAGE2_RETIRE_RESTART_RELOAD_PASS' "$OUT/retire-verdict.txt"
fatal_check

echo 'STAGE2_RESIDUAL_RUNTIME_PASS' | tee "$OUT/STAGE2_RESIDUAL_RUNTIME_RESULT.txt"
'''


class RetirementPolicyTests(unittest.TestCase):
    def test_prepare_makes_retirement_only_reload_gate(self):
        mod = load_module(ROOT / 'stage2_residual_tools/prepare_stage2_retirement_persistence.py', 'prep')
        out = mod.prepare(FIXTURE)
        self.assertIn('build_probe retire', out)
        self.assertNotIn('build_probe accept', out)
        self.assertNotIn('run_scenario accept', out)
        self.assertNotIn('retire second stock retirement writer no-op', out)
        self.assertIn("wait_log 'LoadCareer saveslot: 0'", out)
        self.assertNotIn("wait_log '>>>> RETIRED'", out)
        self.assertIn("wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 30 retire-reload-gamemenu", out)
        self.assertIn("grep -q '>>>> RETIRED' \"$FLOW\"", out)
        self.assertIn('verify_stage2_retirement_persistence.py', out)
        self.assertIn('STAGE2_RETIREMENT_PERSISTENCE_RUNTIME_PASS', out)

    def test_prepare_fails_closed_on_drift(self):
        mod = load_module(ROOT / 'stage2_residual_tools/prepare_stage2_retirement_persistence.py', 'prep2')
        with self.assertRaises(SystemExit):
            mod.prepare(FIXTURE.replace('build_probe reject', 'build_probe decline'))

    def test_prepare_applies_to_historical_gate_exactly(self):
        mod = load_module(ROOT / 'stage2_residual_tools/prepare_stage2_retirement_persistence.py', 'prep3')
        text = (ROOT / 'stage2_residual_gate.sh').read_text(encoding='utf-8')
        out = mod.prepare(text)
        self.assertEqual(out.count('build_probe retire'), 1)
        self.assertEqual(out.count('run_scenario retire'), 1)
        self.assertNotIn('run_scenario accept', out)
        self.assertNotIn('retire second stock retirement writer no-op', out)
        self.assertIn("grep -q '>>>> RETIRED' \"$FLOW\"", out)
        self.assertIn("wait_log 'LoadCareer saveslot: 0' 30 retire-loadcareer", out)
        self.assertIn("wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 30 retire-reload-gamemenu", out)
        self.assertNotIn("wait_log '>>>> RETIRED' 30 retire-retired", out)

    def test_workflow_uses_single_line_bash_wrapper(self):
        wrapper = ROOT / 'stage2_retirement_runtime_gate.sh'
        self.assertTrue(wrapper.exists(), 'runtime wrapper must exist')
        workflow = (ROOT / '.github/workflows/nss-stage2-retirement-persistence.yml').read_text(encoding='utf-8')
        self.assertIn('script: bash stage2_retirement_runtime_gate.sh', workflow)
        self.assertNotIn("bash -eu -o pipefail <<'BASH'", workflow)


if __name__ == '__main__':
    unittest.main()
