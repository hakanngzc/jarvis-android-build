#!/usr/bin/env python3
import subprocess, sys, tempfile, unittest
from pathlib import Path
from stage7_tools.patch_stage7_persistence_probe import build_probe_units, SENTINELS
from stage7_tools.verify_stage7_persistence_runtime import verify_checkpoints

class ProbeEncodingTests(unittest.TestCase):
    def test_mutate_probe_contains_all_six_sentinels_and_stock_save_call(self):
        fields={k:i+100 for i,k in enumerate(('g_player','m_bank','m_items','m_sponsors','m_spenttime','m_technique','m_iapAgent1'))}
        units=build_probe_units('mutate', fields, 900)
        self.assertGreater(len(units), 20)
        for value in SENTINELS.values():
            self.assertIn(value & 0xffff, units)
        self.assertIn(900, units)
        self.assertEqual(0x000e, units[-1])

    def test_save_only_probe_never_embeds_mutation_sentinels(self):
        fields={'g_player':100}
        units=build_probe_units('save-only', fields, 900)
        for value in SENTINELS.values():
            self.assertNotIn(value & 0xffff, units)
        self.assertEqual(0x000e, units[-1])

class ScriptInvocationTests(unittest.TestCase):
    def test_verifier_can_run_as_direct_script(self):
        script=Path(__file__).resolve().parent/'stage7_tools'/'verify_stage7_persistence_runtime.py'
        cp=subprocess.run([sys.executable,str(script)],text=True,capture_output=True)
        self.assertNotEqual(0,cp.returncode)
        self.assertIn('usage: verify_stage7_persistence_runtime.py',cp.stderr+cp.stdout)
        self.assertNotIn('ImportError',cp.stderr+cp.stdout)

class RuntimeVerifierTests(unittest.TestCase):
    def xml(self, tokens):
        state='meta;'+','.join(map(str,tokens))+';club;comp;extra'
        return f'<map><string name=".monkeystate">{state}</string></map>'

    def test_verifier_requires_each_representative_sentinel_to_survive_reload(self):
        pre=list(range(40))
        mutated=pre[:]
        idxs=[2,5,8,11,14,17]
        for idx,val in zip(idxs,SENTINELS.values()): mutated[idx]=val
        reloaded=mutated[:]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for name,tok in [('pre',pre),('mutated',mutated),('update',mutated),('reloaded',reloaded)]:
                (p/f'{name}.xml').write_text(self.xml(tok),encoding='utf-8')
            flow='LoadCareer saveslot: 0\nCreate Screen: gamemenu\nSAVE CAREER\nSAVE CAREER\n'
            result=verify_checkpoints(p/'pre.xml',p/'mutated.xml',p/'update.xml',p/'reloaded.xml',flow)
        self.assertTrue(result['ok'])
        self.assertEqual(6,len(result['sentinel_token_indexes']))

    def test_verifier_fails_when_reload_loses_one_sentinel(self):
        pre=list(range(40)); mutated=pre[:]; idxs=[2,5,8,11,14,17]
        for idx,val in zip(idxs,SENTINELS.values()): mutated[idx]=val
        reloaded=mutated[:]; reloaded[idxs[-1]]=pre[idxs[-1]]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for name,tok in [('pre',pre),('mutated',mutated),('update',mutated),('reloaded',reloaded)]:
                (p/f'{name}.xml').write_text(self.xml(tok),encoding='utf-8')
            result=verify_checkpoints(p/'pre.xml',p/'mutated.xml',p/'update.xml',p/'reloaded.xml','LoadCareer saveslot: 0\nCreate Screen: gamemenu\nSAVE CAREER\nSAVE CAREER\n')
        self.assertFalse(result['ok'])
        self.assertTrue(any('reload lost' in e for e in result['errors']))

    def test_verifier_fails_if_same_signature_update_touches_preferences(self):
        pre=list(range(40)); mutated=pre[:]; idxs=[2,5,8,11,14,17]
        for idx,val in zip(idxs,SENTINELS.values()): mutated[idx]=val
        changed_after_update=mutated[:]; changed_after_update[30]=999
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for name,tok in [('pre',pre),('mutated',mutated),('update',changed_after_update),('reloaded',mutated)]:
                (p/f'{name}.xml').write_text(self.xml(tok),encoding='utf-8')
            result=verify_checkpoints(p/'pre.xml',p/'mutated.xml',p/'update.xml',p/'reloaded.xml','LoadCareer saveslot: 0\nCreate Screen: gamemenu\nSAVE CAREER\nSAVE CAREER\n')
        self.assertFalse(result['ok'])
        self.assertTrue(any('package update changed saved state' in e for e in result['errors']))

if __name__=='__main__': unittest.main()
