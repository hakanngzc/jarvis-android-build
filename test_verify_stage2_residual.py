import unittest

from stage2_residual_tools.verify_stage2_residual import verify_scenario


BASE = {
    'sdate': 200, 'clubnationid': 193, 'clubid': 3141,
    'goalbonus': 10, 'wage': 100, 'lastnegotiations': 150,
    'lasttransferdate': 140, 'playerrecordsha256': 'base',
    'playerrecordnodatesha256': 'base-nodate',
    'clubrecordsha256': 'club', 'competitionrecordsha256': 'comp',
    'additionalclubrecordsha256': 'extra',
}


def cp(**kw):
    out = dict(BASE)
    out.update(kw)
    return out


class VerifyStage2ResidualTests(unittest.TestCase):
    def test_accept(self):
        post = cp(wage=120, goalbonus=12, lastnegotiations=200, lasttransferdate=200,
                  playerrecordsha256='accept', playerrecordnodatesha256='accept-nodate')
        self.assertTrue(verify_scenario('accept', BASE, post, dict(post))['pass'])

    def test_reject(self):
        post = cp(lastnegotiations=200, playerrecordsha256='reject', playerrecordnodatesha256='reject-nodate')
        self.assertTrue(verify_scenario('reject', BASE, post, dict(post))['pass'])

    def test_transfer(self):
        post = cp(clubid=3157, lastnegotiations=200, lasttransferdate=200,
                  playerrecordsha256='transfer', playerrecordnodatesha256='transfer-nodate')
        self.assertTrue(verify_scenario('transfer', BASE, post, dict(post), destination_club_id=3157)['pass'])

    def test_retire_uses_stock_retired_mainmenu_boundary(self):
        post = cp(sdate=199, playerrecordsha256='retired', playerrecordnodatesha256='retired-nodate')
        result = verify_scenario('retire', BASE, post, dict(post), retire_restart_mainmenu=True)
        self.assertTrue(result['pass'])
        self.assertTrue(result['checks']['retirement_state_changed_beyond_date'])
        self.assertTrue(result['checks']['retired_restart_mainmenu_reached'])
        self.assertNotIn('second_probe_checkpoint_supplied', result['checks'])

    def test_retire_fails_if_only_date_changed(self):
        post = cp(sdate=199, playerrecordsha256='date-only', playerrecordnodatesha256=BASE['playerrecordnodatesha256'])
        self.assertFalse(verify_scenario('retire', BASE, post, dict(post), retire_restart_mainmenu=True)['pass'])

    def test_retire_fails_without_restart_mainmenu_proof(self):
        post = cp(sdate=199, playerrecordsha256='retired', playerrecordnodatesha256='retired-nodate')
        self.assertFalse(verify_scenario('retire', BASE, post, dict(post), retire_restart_mainmenu=False)['pass'])

    def test_restart_mismatch_fails(self):
        post = cp(wage=120, goalbonus=12, lastnegotiations=200, lasttransferdate=200,
                  playerrecordsha256='accept', playerrecordnodatesha256='accept-nodate')
        restart = dict(post); restart['wage'] = 999
        self.assertFalse(verify_scenario('accept', BASE, post, restart)['pass'])


if __name__ == '__main__':
    unittest.main()
