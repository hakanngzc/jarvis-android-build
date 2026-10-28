#!/usr/bin/env python3
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

class Stage9CrossVersionGateTests(unittest.TestCase):
    def setUp(self):
        self.post=(ROOT/'stage9_postmatch_gate.sh').read_text(encoding='utf-8') if (ROOT/'stage9_postmatch_gate.sh').exists() else ''
        self.workflow=(ROOT/'.github/workflows/nss-stage9-cross-version.yml').read_text(encoding='utf-8') if (ROOT/'.github/workflows/nss-stage9-cross-version.yml').exists() else ''

    def test_workflow_runs_same_gate_on_android10_and_android14(self):
        self.assertIn('api-level: [29, 34]', self.workflow)
        self.assertIn('bash stage7_runtime_gate.sh', self.workflow)
        self.assertIn('bash stage8_navigation_gate.sh', self.workflow)
        self.assertIn('bash stage8_match_lifecycle_gate.sh', self.workflow)
        self.assertIn('bash stage9_postmatch_gate.sh', self.workflow)
        order=[self.workflow.index(x) for x in (
            'bash stage7_runtime_gate.sh','bash stage8_navigation_gate.sh',
            'bash stage8_match_lifecycle_gate.sh','bash stage9_postmatch_gate.sh')]
        self.assertEqual(order, sorted(order))

    def test_postmatch_gate_requires_real_matchreview_activation(self):
        self.assertIn("wait_state 'matchreview'", self.post)
        self.assertIn('STAGE9_MATCHREVIEW_REACHED', self.post)
        self.assertNotIn('Create Screen:[[:space:]]*matchreview', self.post)

    def test_postmatch_gate_requires_stock_save_and_restart_reload(self):
        self.assertIn("wait_log 'SAVE CAREER|SaveCareer|SaveState'", self.post)
        self.assertIn('postmatch-before-restart-MonkeyGame.xml', self.post)
        self.assertIn('am force-stop "$PKG"', self.post)
        self.assertIn("wait_log 'LoadCareer saveslot:[[:space:]]*0'", self.post)
        self.assertIn('postmatch-after-restart-MonkeyGame.xml', self.post)
        self.assertIn('verify_stage8_lifecycle.py', self.post)
        self.assertIn('STAGE9_POSTMATCH_RELOAD_PASS', self.post)

    def test_postmatch_gate_rejects_nss_crash_or_anr(self):
        self.assertIn('ANR in com\\.newstargames\\.newstarsoccer', self.post)
        self.assertIn('FATAL EXCEPTION.*com\\.newstargames\\.newstarsoccer', self.post)

    def test_workflow_uploads_version_scoped_evidence(self):
        self.assertIn('stage9-final-api${{ matrix.api-level }}', self.workflow)
        self.assertIn('${{ runner.temp }}/stage7-persistence/', self.workflow)
        self.assertIn('${{ runner.temp }}/stage8-navigation/', self.workflow)
        self.assertIn('${{ runner.temp }}/stage8-match-lifecycle/', self.workflow)
        self.assertIn('${{ runner.temp }}/stage9-cross-version/', self.workflow)

if __name__=='__main__': unittest.main()
