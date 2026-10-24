import unittest
from patch_lifecycle_probe import patch_script

FIXTURE = '''#!/usr/bin/env bash
sign_one(){
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  echo "$src $dst $aligned"
}
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }

start_menu(){ echo menu; }

# Fresh disposable Career.
start_menu
adb shell wm size > "$OUT/wm-size.txt"
shot saveslot
find_slot0_target "$OUT/saveslot.png" "$WORK/slot0.txt"
read -r SLOT_X SLOT_Y < "$WORK/slot0.txt"
clear_log
press_physical "$SLOT_X" "$SLOT_Y" 3
shot career-gamemenu

# Drive normal stock UI to the next playable match.
clear_log
press_play 2
sleep 1
shot "knockout-$MODE-t1"
'''

class LifecyclePatchTest(unittest.TestCase):
    def test_injects_three_lifecycle_checks(self):
        out = patch_script(FIXTURE)
        self.assertIn('lifecycle_warm_relaunch mainmenu', out)
        self.assertIn('lifecycle_background_roundtrip career', out)
        self.assertIn('lifecycle_background_roundtrip match', out)
        self.assertIn('LIFECYCLE_RUNTIME_RESULT.txt', out)

    def test_isolates_warm_relaunch_from_career_navigation(self):
        out = patch_script(FIXTURE)
        self.assertIn('lifecycle_warm_relaunch mainmenu\nstart_menu\nadb shell wm size', out)

    def test_uses_stable_logical_slot1_new_career_target(self):
        out = patch_script(FIXTURE)
        self.assertIn('read -r SLOT_X SLOT_Y < <(logical_xy 320 280)', out)
        self.assertNotIn('find_slot0_target "$OUT/saveslot.png"', out)

    def test_repairs_latent_sign_one_nounset_bug(self):
        out = patch_script(FIXTURE)
        self.assertIn('local src="$1" dst="$2"\n  local aligned=', out)
        self.assertNotIn('local src="$1" dst="$2" aligned=', out)

    def test_refuses_changed_source_anchors(self):
        with self.assertRaises(ValueError):
            patch_script(FIXTURE.replace('shot career-gamemenu', 'shot changed'))

if __name__ == '__main__': unittest.main()
