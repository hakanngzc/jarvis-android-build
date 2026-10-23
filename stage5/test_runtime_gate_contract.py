import unittest
from pathlib import Path


class Stage5RuntimeGateContractTests(unittest.TestCase):
    def test_runtime_gate_proves_same_save_survives_name_only_update(self):
        text = Path('stage5/run_save_compat.sh').read_text(encoding='utf-8')
        required = (
            "EXPECTED_XAPK='afa4c3319e275de558da7a1c253dec84964094b0a4c1cb2ad557f53dbaf5b57e'",
            "EXPECTED_BASE='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'",
            'stage5.name_only_patch',
            'adb root',
            'shared_prefs/MonkeyGame.xml',
            'SAVE_SHA_BEFORE',
            'SAVE_SHA_AFTER_UPDATE',
            'install-multiple -r',
            'LoadCareer saveslot:[[:space:]]*0',
            'STAGE5_NAME_ONLY_OLD_SAVE_COMPAT_PASS',
        )
        for token in required:
            with self.subTest(token=token):
                self.assertIn(token, text)

        # The updated package must preserve app data; clearing after the first save
        # would invalidate the old-save compatibility proof.
        update_marker = text.index('NAME_ONLY_UPDATE_BEGIN')
        self.assertNotIn('pm clear', text[update_marker:])


if __name__ == '__main__':
    unittest.main()
