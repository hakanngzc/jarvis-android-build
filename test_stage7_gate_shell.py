import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent

class Stage7GateShellTests(unittest.TestCase):
    def test_gate_keeps_stock_save_load_and_checks_restart(self):
        text=(ROOT/'stage7_persistence_gate.sh').read_text()
        self.assertIn('patch_stage7_persistence_probe.py',text)
        self.assertIn('verify_stage7_persistence_runtime.py',text)
        self.assertIn('post-save-MonkeyGame.xml',text)
        self.assertIn('post-restart-MonkeyGame.xml',text)
        self.assertIn("wait_log 'SAVE CAREER|SaveCareer|SaveState'",text)
        self.assertIn("wait_log 'LoadCareer saveslot:[[:space:]]*0'",text)
        self.assertIn('STAGE7_PERSISTENCE_RUNTIME_PASS',text)
        self.assertNotIn('pm clear "$PKG"', text.split('# Install Stage7 probe update')[1])
        self.assertNotIn('local src="$1" dst="$2" tmp=', text)
        self.assertIn('local src="$1"', text)
        self.assertIn('local dst="$2"', text)
        self.assertIn('local tmp="$WORK/aligned-$(basename "$dst")"', text)

if __name__=='__main__':
    unittest.main()

# Clean rerun trigger after signing-helper regression fix.
