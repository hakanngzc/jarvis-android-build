import tempfile
import unittest
from pathlib import Path

from stage7_tools.verify_stage7_persistence_runtime import verify_snapshots, SENTINEL_TEXT

def xml_for(tokens):
    state='slotmeta;'+','.join(tokens)+';club;comp;extra'
    return f'<?xml version="1.0" encoding="utf-8" standalone="yes" ?><map><string name=".monkeystate">{state}</string></map>'

class Stage7RuntimeVerifierTests(unittest.TestCase):
    def test_post_and_restart_require_all_sentinels(self):
        pre=['1','2','3','normal']; post=['1','2','3']+list(SENTINEL_TEXT.values())+['tail']
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for name,tokens in [('pre',pre),('post',post),('restart',post)]:
                (p/f'{name}.xml').write_text(xml_for(tokens),encoding='utf-8')
            result=verify_snapshots(p/'pre.xml',p/'post.xml',p/'restart.xml','SAVE CAREER\nLoadCareer saveslot: 0\n')
        self.assertTrue(result['passed'])

    def test_missing_sponsor_sentinel_fails(self):
        post=list(SENTINEL_TEXT.values()); post.remove(SENTINEL_TEXT['sponsors0'])
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)
            for name,tokens in [('pre',['x']),('post',post),('restart',post)]:
                (p/f'{name}.xml').write_text(xml_for(tokens),encoding='utf-8')
            result=verify_snapshots(p/'pre.xml',p/'post.xml',p/'restart.xml','SAVE CAREER\nLoadCareer saveslot: 0\n')
        self.assertFalse(result['passed'])
        self.assertIn('post contains sponsor sentinel',[x['label'] for x in result['checks'] if not x['ok']])

if __name__=='__main__':unittest.main()
