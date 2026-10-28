#!/usr/bin/env python3
import re, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent

class Stage7RuntimeGateTests(unittest.TestCase):
    def setUp(self):
        self.shell=(ROOT/'stage7_runtime_gate.sh').read_text(encoding='utf-8')
        self.workflow=(ROOT/'.github/workflows/nss-stage7-persistence-runtime.yml').read_text(encoding='utf-8')

    def test_career_press_uses_long_physical_touch(self):
        m=re.search(r'press_career\(\)\{(?P<body>.*?)\n\}',self.shell,re.S)
        self.assertIsNotNone(m)
        self.assertIn('press_physical 795 1399',m.group('body'))
        self.assertNotIn('input touchscreen tap 795 1399',m.group('body'))

    def test_play_press_uses_long_physical_touch(self):
        m=re.search(r'press_play\(\)\{(?P<body>.*?)\n\}',self.shell,re.S)
        self.assertIsNotNone(m)
        self.assertIn('press_physical 935 1850',m.group('body'))
        self.assertNotIn('input touchscreen tap 935 1850',m.group('body'))

    def test_sign_one_assigns_tmp_only_after_dst_is_initialized(self):
        m=re.search(r'sign_one\(\)\{(?P<body>.*?)\n\}',self.shell,re.S)
        self.assertIsNotNone(m)
        body=m.group('body')
        self.assertIn('local src="$1" dst="$2" tmp',body)
        self.assertIn('tmp="$WORK/aligned-$(basename "$dst")"',body)
        self.assertNotRegex(body,r'local[^\n]*tmp=.*\$dst')
        self.assertLess(body.index('local src="$1" dst="$2" tmp'),body.index('tmp="$WORK/aligned-$(basename "$dst")"'))

    def test_gate_uses_exact_public_stock_431_hashes(self):
        self.assertIn("afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e",self.shell)
        self.assertIn("46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4",self.shell)

    def test_gate_runs_mutate_then_save_only_probe(self):
        self.assertIn('patch_stage7_persistence_probe.py "$WORK/base-career-unsigned.apk" "$WORK/base-stage7-mutate-unsigned.apk" mutate',self.shell)
        self.assertIn('patch_stage7_persistence_probe.py "$WORK/base-career-unsigned.apk" "$WORK/base-stage7-saveonly-unsigned.apk" save-only',self.shell)
        self.assertLess(self.shell.index('base-stage7-mutate-unsigned.apk'),self.shell.index('base-stage7-saveonly-unsigned.apk'))

    def test_fresh_bootstrap_resolves_webpagenews_before_dump_save(self):
        marker='bootstrap_saved=0'
        self.assertIn(marker,self.shell)
        block=self.shell.split(marker,1)[1].split('dump_save pre',1)[0]
        self.assertIn('for bootstrap_step in $(seq 1 30)',block)
        self.assertIn('bootstrap_state="$(latest_bootstrap_state)"',block)
        self.assertIn('webpage)',block)
        webpage=block.split('webpage)',1)[1].split(';;',1)[0]
        self.assertIn('press_footer_ok 2',webpage)
        self.assertIn('message|startransition)',block)
        self.assertIn('press_message_accept 2',block)
        self.assertIn('gamemenu)',block)
        self.assertIn('bootstrap_gamemenu=1',block)
        self.assertIn('[ "$bootstrap_saved" -eq 1 ]',block)
        self.assertIn('[ "$bootstrap_gamemenu" -eq 1 ]',block)
        self.assertNotIn("wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 40 fresh-gamemenu || true",self.shell)

    def test_setup_only_restarts_and_proves_slot0_load_before_ready(self):
        marker='if [ "${STAGE7_SETUP_ONLY:-0}" = 1 ]; then'
        self.assertIn(marker,self.shell)
        block=self.shell.split(marker,1)[1].split('\nfi',1)[0]
        self.assertIn('adb shell am force-stop "$PKG"',block)
        self.assertIn('adb shell am start -n "$PKG/.MonkeyGame"',block)
        self.assertIn("wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 setup-only-loadcareer",block)
        self.assertIn("wait_log 'Create Screen:[[:space:]]*gamemenu|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' 60 setup-only-gamemenu",block)
        self.assertIn("echo 'STAGE7_RUNTIME_BASE_READY'",block)
        self.assertLess(block.index('setup-only-loadcareer'),block.index("echo 'STAGE7_RUNTIME_BASE_READY'"))
        self.assertLess(block.index('setup-only-gamemenu'),block.index("echo 'STAGE7_RUNTIME_BASE_READY'"))

    def test_update_is_verified_before_process_death_reload(self):
        marker='# Same-signature save-only update must not touch the durable save.'
        self.assertIn(marker,self.shell)
        block=self.shell.split(marker,1)[1]
        self.assertIn('dump_save after-update',block)
        self.assertIn('am force-stop',block)
        self.assertLess(block.index('dump_save after-update'),block.index('am force-stop'))
        self.assertIn("wait_log 'LoadCareer saveslot:[[:space:]]*0' 60 reload-loadcareer",block)

    def test_reload_proof_reserializes_ram_without_mutating_sentinels(self):
        self.assertIn('trigger_probe reload-saveonly',self.shell)
        self.assertIn('dump_save post-reload-resave',self.shell)
        self.assertIn('verify_stage7_persistence_runtime.py',self.shell)
        self.assertIn('pre-MonkeyGame.xml',self.shell)
        self.assertIn('post-mutation-MonkeyGame.xml',self.shell)
        self.assertIn('after-update-MonkeyGame.xml',self.shell)
        self.assertIn('post-reload-resave-MonkeyGame.xml',self.shell)

    def test_all_adb_calls_are_bounded(self):
        m=re.search(r'adb\(\)\s*\{(?P<body>.*?)\n\}',self.shell,re.S)
        self.assertIsNotNone(m)
        self.assertIn('timeout --signal=TERM --kill-after=5s 45s',m.group('body'))
        self.assertIn('last-adb-command.txt',m.group('body'))

    def test_workflow_is_pinned_and_api29(self):
        self.assertIn('runs-on: ubuntu-24.04',self.workflow)
        self.assertIn('actions/checkout@11d5960a326750d5838078e36cf38b85af677262',self.workflow)
        self.assertIn('reactivecircus/android-emulator-runner@a421e43855164a8197daf9d8d40fe71c6996bb0d',self.workflow)
        self.assertIn('actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02',self.workflow)
        self.assertIn('api-level: 29',self.workflow)
        self.assertIn('bash stage7_runtime_gate.sh',self.workflow)

if __name__=='__main__':unittest.main()
