import unittest

from patch_lifecycle_probe_v3 import harden_generated_script

FIXTURE = r'''lifecycle_background_roundtrip(){
  local tag="$1" before hidden after
  lifecycle_record "${tag}_background_process_survived" PASS
  adb shell am start -n "$PKG/.MonkeyGame" >/dev/null 2>&1 || true
  sleep 3
  after="$(pid_one)"
}
reload_saved_career_after_setup(){
  start_menu
  clear_log
  press_physical 810 1450 2
  wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 lifecycle-reload-saveslot
}
start_menu
adb shell wm size > "$OUT/wm-size.txt"
clear_log
press_physical 810 1450 2
wait_log 'Create Screen:[[:space:]]*saveslot|SetActive:[[:space:]]*saveslot|SETTING ACTIVE:[[:space:]]*saveslot' 25 saveslot
'''


class LifecyclePatchV3Test(unittest.TestCase):
    def test_background_foreground_uses_recents_not_am_start(self):
        out = harden_generated_script(FIXTURE)
        self.assertIn('foreground_from_recents "$tag" || return 1', out)
        self.assertIn('adb shell input keyevent 187', out)
        self.assertIn('adb shell input tap "$x" "$y"', out)
        self.assertNotIn('adb shell am start -n "$PKG/.MonkeyGame"', out)

    def test_recents_requires_nss_to_be_resumed(self):
        out = harden_generated_script(FIXTURE)
        self.assertIn('lifecycle-${tag}-recents-activity.txt', out)
        self.assertIn('"${tag}_recents_foreground" FAIL', out)
        self.assertIn('"${tag}_recents_foreground" PASS', out)

    def test_career_entry_uses_scaled_logical_target_and_retries(self):
        out = harden_generated_script(FIXTURE)
        self.assertIn('logical_xy 480 664', out)
        self.assertIn('for attempt in 1 2 3', out)
        self.assertIn('open_saveslot_from_mainmenu saveslot', out)
        self.assertIn('open_saveslot_from_mainmenu lifecycle-reload-saveslot', out)
        self.assertNotIn('press_physical 810 1450 2', out)

    def test_refuses_changed_roundtrip_shape(self):
        with self.assertRaises(ValueError):
            harden_generated_script(FIXTURE.replace('adb shell am start -n "$PKG/.MonkeyGame"', 'echo changed'))


if __name__ == '__main__':
    unittest.main()
