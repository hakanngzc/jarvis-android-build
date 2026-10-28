#!/usr/bin/env python3
import subprocess, sys, tempfile, unittest
from pathlib import Path
from stage8_tools.verify_stage8_lifecycle import compare_checkpoints

ROOT=Path(__file__).resolve().parent
BASE={
    'sdate':12,'clubnationid':43,'clubid':6057,'fullname':'A Player','shortname':'Player',
    'careerapps':0,'goalbonus':1,'wage':5,'lastnegotiations':0,'lasttransferdate':0,
    'playerrecordsha256':'player-a','clubrecordsha256':'club-a','competitionrecordsha256':'comp-a','additionalclubrecordsha256':'add-a'
}

class LifecycleVerifierTests(unittest.TestCase):
    def test_allows_player_record_hash_change_when_stable_contract_matches(self):
        post=dict(BASE); post['playerrecordsha256']='player-b'
        r=compare_checkpoints(BASE,post)
        self.assertTrue(r['ok'],r)

    def test_rejects_club_identity_change(self):
        post=dict(BASE); post['clubid']=999
        r=compare_checkpoints(BASE,post)
        self.assertFalse(r['ok'])
        self.assertTrue(any('clubid' in e for e in r['errors']))

    def test_rejects_competition_block_change(self):
        post=dict(BASE); post['competitionrecordsha256']='comp-b'
        r=compare_checkpoints(BASE,post)
        self.assertFalse(r['ok'])
        self.assertTrue(any('competitionrecordsha256' in e for e in r['errors']))

    def test_direct_script_resolves_repo_local_stage3_tools(self):
        proc=subprocess.run(
            [sys.executable, str(ROOT/'stage8_tools/verify_stage8_lifecycle.py')],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(proc.returncode,0)
        self.assertIn('usage: verify_stage8_lifecycle.py PRE_XML POST_XML',proc.stderr)
        self.assertNotIn('ModuleNotFoundError',proc.stderr)

if __name__=='__main__':unittest.main()
