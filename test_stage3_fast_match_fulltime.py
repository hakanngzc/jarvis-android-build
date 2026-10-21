import unittest

from stage3_tools.patch_stage3_fast_match_probe import build_probe_units


class Stage3FastMatchFullTimeTest(unittest.TestCase):
    def test_probe_emits_stock_full_time_state_transition(self):
        fixture_id = 0x1111
        score1_id = 0x2222
        score2_id = 0x3333
        over_id = 0x4444
        matchstate_id = 0x5555
        half_id = 0x6666
        matchmin_id = 0x7777
        gs_over_id = 0x8888
        do_half_end_id = 0x9999

        units = build_probe_units(
            fixture_id,
            score1_id,
            score2_id,
            over_id,
            matchstate_id,
            half_id,
            matchmin_id,
            gs_over_id,
            do_half_end_id,
        )

        self.assertEqual(
            units,
            [
                0x0062, fixture_id,              # sget-object v0, m_fixture
                0x1112,                          # const/4 v1, 1
                0x0159, score1_id,               # iput v1, v0, m_score1
                0x0112,                          # const/4 v1, 0
                0x0159, score2_id,               # iput v1, v0, m_score2
                0x0113, 0x005A,                  # const/16 v1, 90
                0x0167, matchmin_id,             # sput v1, m_matchmin
                0x3112,                          # const/4 v1, 3 (stock full-time half)
                0x0167, half_id,                 # sput v1, m_half
                0x1112,                          # const/4 v1, 1 (true)
                0x1071, over_id, 0x0001,         # invoke-static {v1}, m_MatchOver(Z)I
                0x000A,                          # move-result v0
                0x0038, 0x000B,                  # if-eqz v0, return
                0x5112,                          # const/4 v1, 5
                0x0167, matchstate_id,           # sput v1, m_matchstate
                0x0071, gs_over_id, 0x0000,      # invoke-static {}, g_GSOnMatchOver()V
                0x0071, do_half_end_id, 0x0000,  # invoke-static {}, TScreen_Match.m_DoHalfEnd()I handoff
                0x000F,                          # return v0
            ],
        )


if __name__ == '__main__':
    unittest.main()
