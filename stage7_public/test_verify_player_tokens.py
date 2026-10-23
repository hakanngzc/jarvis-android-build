import tempfile,unittest
from pathlib import Path

from verify_player_tokens import extract_player_tokens,verify_expected,compare_expected

EXPECTED={5:'61.25',6:'62.5',7:'63.75',8:'64.5',9:'65.25',10:'66.5',11:'17.25',12:'18.5',33:'77',34:'321',35:'4321',68:'7',69:'3',71:'71',72:'72',73:'73',74:'74',75:'75',576:'5',581:'12344',582:'12345'}


def xml_for(player):
    # index 0 shared global, index 1 slot0 player
    state='global;'+','.join(player)+';club;comp;extra'
    return f'''<?xml version="1.0" encoding="utf-8" standalone="yes" ?><map><string name=".monkeystate">{state}</string></map>'''


class PlayerTokenVerifierTests(unittest.TestCase):
    def make(self,values):
        tokens=['0']*600
        for i,v in values.items(): tokens[i]=v
        td=tempfile.TemporaryDirectory(); p=Path(td.name)/'MonkeyGame.xml'; p.write_text(xml_for(tokens),encoding='utf-8')
        self.addCleanup(td.cleanup); return p,tokens

    def test_extracts_slot0_player_and_checks_exact_indices(self):
        p,tokens=self.make(EXPECTED)
        got=extract_player_tokens(p,slot=0)
        self.assertEqual(len(got),600)
        report=verify_expected(got,EXPECTED)
        self.assertTrue(report['pass'],report)
        self.assertEqual(report['values']['35'],'4321')
        self.assertEqual(report['values']['582'],'12345')

    def test_rejects_wrong_value_at_exact_index(self):
        bad=dict(EXPECTED); bad[35]='4320'
        p,_=self.make(bad)
        report=verify_expected(extract_player_tokens(p),EXPECTED)
        self.assertFalse(report['pass'])
        self.assertIn('35',report['mismatches'])

    def test_compare_requires_same_expected_tokens_before_and_after(self):
        a,_=self.make(EXPECTED); b,_=self.make(EXPECTED)
        report=compare_expected(extract_player_tokens(a),extract_player_tokens(b),EXPECTED)
        self.assertTrue(report['pass'],report)
        bad=dict(EXPECTED); bad[71]='70'; c,_=self.make(bad)
        report=compare_expected(extract_player_tokens(a),extract_player_tokens(c),EXPECTED)
        self.assertFalse(report['pass'])
        self.assertIn('71',report['after']['mismatches'])

    def test_fails_closed_on_short_player_block(self):
        td=tempfile.TemporaryDirectory(); self.addCleanup(td.cleanup)
        p=Path(td.name)/'MonkeyGame.xml'; p.write_text(xml_for(['0']*100),encoding='utf-8')
        with self.assertRaises(ValueError): verify_expected(extract_player_tokens(p),EXPECTED)


if __name__=='__main__': unittest.main()
