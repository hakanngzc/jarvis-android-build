import unittest

from stage3_reload_autoload_patch import patch_text


BASE = '''# Restart, reload the same Career, then prove match state persisted.
adb shell am force-stop "$PKG" >/dev/null 2>&1 || true
start_game reload
open_slot0 reload
load_existing reload
sleep 2; dump_save post-restart
capture_log 'Stage3 after restart/load'
'''


class Stage3ReloadAutoloadPatchTest(unittest.TestCase):
    def test_auto_loaded_gamemenu_skips_manual_saveslot_path(self):
        out = patch_text(BASE)
        self.assertIn("reload-auto-gamemenu", out)
        self.assertIn("Auto-loaded Career detected after restart", out)
        self.assertIn("open_slot0 reload", out)  # fallback remains available
        self.assertIn("load_existing reload", out)
        self.assertIn("dump_save post-restart", out)
        self.assertIn("CallFunc:[[:space:]]*LoadCareer", out)

    def test_patch_refuses_missing_anchor(self):
        with self.assertRaises(ValueError):
            patch_text("unrelated")


if __name__ == '__main__':
    unittest.main()
