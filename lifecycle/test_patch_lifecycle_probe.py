import unittest
from patch_lifecycle_probe import patch_script

POST_CREATE = '''for _ in 1 2 3 4 5; do
  press_message_accept 2
  fatal_check
  adb logcat -d -v threadtime > "$WORK/save-progress.txt" 2>/dev/null || true
  if grep -qE 'CAREER STARTED|SAVE CAREER|SaveCareer|SaveState|SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu' "$WORK/save-progress.txt"; then break; fi
done
wait_log 'SETTING ACTIVE:[[:space:]]*gamemenu|SetActive:[[:space:]]*gamemenu|Create Screen:[[:space:]]*gamemenu' 35 gamemenu'''

FIXTURE = f'''#!/usr/bin/env bash
sign_one(){{
  local src="$1" dst="$2" aligned="$WORK/aligned-$(basename "$dst")"
  echo "$src $dst $aligned"
}}
clear_log(){{ adb logcat -c >/dev/null 2>&1 || true; }}

start_menu(){{ echo menu; }}

# Fresh disposable Career.
start_menu
adb shell wm size > "$OUT/wm-size.txt"
shot saveslot
find_slot0_target "$OUT/saveslot.png" "$WORK/slot0.txt"
read -r SLOT_X SLOT_Y < "$WORK/slot0.txt"
clear_log
press_physical "$SLOT_X" "$SLOT_Y" 3
{POST_CREATE}
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

    def test_reloads_saved_career_instead_of_blind_onboarding_taps(self):
        out = patch_script(FIXTURE)
        self.assertIn('wait_for_initial_career_save', out)
        self.assertIn('reload_saved_career_after_setup', out)
        self.assertIn("wait_log 'LoadCareer saveslot:[[:space:]]*0'", out)
        self.assertNotIn('for _ in 1 2 3 4 5; do\n  press_message_accept 2', out)

    def test_refuses_changed_source_anchors(self):
        with self.assertRaises(ValueError):
            patch_script(FIXTURE.replace('shot career-gamemenu', 'shot changed'))

if __name__ == '__main__': unittest.main()
