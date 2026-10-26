#!/usr/bin/env python3
import re, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

class Stage8NavigationGateTests(unittest.TestCase):
    def setUp(self):
        self.shell=(ROOT/'stage8_navigation_gate.sh').read_text(encoding='utf-8') if (ROOT/'stage8_navigation_gate.sh').exists() else ''
        self.workflow=(ROOT/'.github/workflows/nss-stage8-navigation-runtime.yml').read_text(encoding='utf-8') if (ROOT/'.github/workflows/nss-stage8-navigation-runtime.yml').exists() else ''

    def test_reuses_stage7_proven_runtime_before_navigation(self):
        self.assertIn('bash stage7_runtime_gate.sh',self.workflow)
        self.assertIn('bash stage8_navigation_gate.sh',self.workflow)
        self.assertLess(self.workflow.index('bash stage7_runtime_gate.sh'),self.workflow.index('bash stage8_navigation_gate.sh'))

    def test_navigation_reinstalls_non_playmatches_probe_base(self):
        self.assertIn('stage7-work/base-career-unsigned.apk',self.shell)
        self.assertIn('patch_stage8_age_unlock.py',self.shell)
        self.assertIn('install-multiple -r',self.shell)
        self.assertNotIn('base-stage7-saveonly.apk',self.shell)

    def test_career_hub_major_nav_coordinates_are_locked(self):
        self.assertIn('route gamemenu-life 405 837 relationships',self.shell)
        self.assertIn('route gamemenu-skills 249 837 skills',self.shell)
        self.assertIn('route gamemenu-league 93 837 league',self.shell)

    def test_relationship_family_routes_are_present(self):
        self.assertIn('route relationships-achievements 561 837 achievements',self.shell)
        self.assertIn('route relationships-lifestyle 249 837 shop',self.shell)
        self.assertIn('route relationships-casino 405 837 casino',self.shell)

    def test_casino_subfamilies_are_present(self):
        for line in (
            'route casino-blackjack 177 352 blackjack',
            'route casino-roulette 469 352 roulette',
            'route casino-slots 177 586 slots',
            'route casino-racing 469 586 racing',
        ):
            self.assertIn(line,self.shell)
        self.assertNotIn('route racing-stable 249 837 mystable',self.shell)

    def test_skills_and_league_child_routes_are_present(self):
        self.assertIn('route skills-skillchoice 580 283 skillchoice',self.shell)
        self.assertIn('route skills-ratings 405 837 ratings',self.shell)
        self.assertIn('route league-clubfixtures 249 837 clubfixtures',self.shell)
        self.assertIn('route gamemenu-leaguefixtures 553 829 leaguefixtures',self.shell)

    def test_ui_back_or_home_paths_are_asserted(self):
        for target in ('relationships','casino','racing','skills','league','gamemenu'):
            self.assertRegex(self.shell,rf'(route|back_route)[^\n]*{target}')

    def test_career_lifecycle_background_foreground_is_guarded(self):
        self.assertIn('career-lifecycle-pre',self.shell)
        self.assertIn('input keyevent 3',self.shell)
        self.assertIn('career-lifecycle-post',self.shell)
        self.assertIn('verify_stage8_lifecycle.py',self.shell)
        self.assertIn('CAREER_LIFECYCLE_PASS',self.shell)
        self.assertNotIn('cmp -s "$OUT/career-lifecycle-pre-MonkeyGame.xml"',self.shell)

    def test_all_adb_calls_are_bounded(self):
        m=re.search(r'adb\(\)\s*\{(?P<body>.*?)\n\}',self.shell,re.S)
        self.assertIsNotNone(m)
        self.assertIn('timeout --signal=TERM --kill-after=5s 45s',m.group('body'))

    def test_workflow_is_pinned_api29_and_uploads_evidence(self):
        self.assertIn('runs-on: ubuntu-24.04',self.workflow)
        self.assertIn('api-level: 29',self.workflow)
        self.assertIn('actions/checkout@11d5960a326750d5838078e36cf38b85af677262',self.workflow)
        self.assertIn('reactivecircus/android-emulator-runner@a421e43855164a8197daf9d8d40fe71c6996bb0d',self.workflow)
        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',self.workflow)
        self.assertIn('stage8-navigation-runtime-evidence',self.workflow)

if __name__=='__main__':unittest.main()
