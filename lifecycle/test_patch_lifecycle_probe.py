import unittest
from patch_lifecycle_probe import patch_script

FIXTURE = '''#!/usr/bin/env bash
clear_log(){ adb logcat -c >/dev/null 2>&1 || true; }

start_menu(){ echo menu; }

# Fresh disposable Career.
start_menu
adb shell wm size > "$OUT/wm-size.txt"
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

    def test_refuses_changed_source_anchors(self):
        with self.assertRaises(ValueError):
            patch_script(FIXTURE.replace('shot career-gamemenu', 'shot changed'))

if __name__ == '__main__': unittest.main()
