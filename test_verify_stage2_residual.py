import unittest

from stage2_residual_tools.verify_stage2_residual import verify_scenario


BASE = {
    'sdate': 200, 'clubnationid': 193, 'clubid': 3141,
    'goalbonus': 10, 'wage': 100, 'lastnegotiations': 150,
    'lasttransferdate': 140, 'playerrecordsha256': 'base',
    'clubrecordsha256': 'club', 'competitionrecordsha256': 'comp',
    'additionalclubrecordsha256': 'extra',
}


def cp(**kw):
    out = dict(BASE)
    out.update(kw)
    return out


class VerifyStage2ResidualTests(unittest.TestCase):
    def test_accept(self):
        post = cp(wage=120, goalbonus=12, lastnegotiations=200, lasttransferdate=200, playerrecordsha256='accept')
        self.assertTrue(verify_scenario('accept', BASE, post, dict(post))['pass'])

    def test_reject(self):
        post = cp(lastnegotiations=200, playerrecordsha256='reject')
        self.assertTrue(verify_scenario('reject', BASE, post, dict(post))['pass'])

    def test_transfer(self):
        post = cp(clubid=3157, lastnegotiations=200, lasttransferdate=200, playerrecordsha256='transfer')
        self.assertTrue(verify_scenario('transfer', BASE, post, dict(post), destination_club_id=3157)['pass'])

    def test_retire(self):
        post = cp(sdate=199, playerrecordsha256='retired')
        result = verify_scenario('retire', BASE, post, dict(post), second_after_reload=dict(post))
        self.assertTrue(result['pass'])

    def test_restart_mismatch_fails(self):
        post = cp(wage=120, goalbonus=12, lastnegotiations=200, lasttransferdate=200, playerrecordsha256='accept')
        restart = dict(post); restart['wage'] = 999
        self.assertFalse(verify_scenario('accept', BASE, post, restart)['pass'])


if __name__ == '__main__':
    unittest.main()
