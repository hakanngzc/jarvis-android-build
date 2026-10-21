#!/usr/bin/env python3
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path


class Stage3AdOverlayStateTest(unittest.TestCase):
    def run_state(self, logcat_text: str, activity_text: str) -> str:
        script = Path("stage3_minimal_gate.sh").read_text(encoding="utf-8")
        match = re.search(r"current_state\(\)\{\n(.*?)\n\}\nwait_state\(\)", script, re.S)
        self.assertIsNotNone(match, "current_state() function not found")
        current_state_fn = "current_state(){\n" + match.group(1) + "\n}\n"

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            fakebin = root / "bin"
            work = root / "work"
            fakebin.mkdir()
            work.mkdir()
            fake_log = root / "logcat.txt"
            fake_activity = root / "activity.txt"
            fake_log.write_text(logcat_text, encoding="utf-8")
            fake_activity.write_text(activity_text, encoding="utf-8")

            adb = fakebin / "adb"
            adb.write_text(
                "#!/usr/bin/env bash\n"
                "if [ \"${1:-}\" = logcat ]; then cat \"$FAKE_LOG\"; exit 0; fi\n"
                "if [ \"${1:-}\" = shell ] && [ \"${2:-}\" = dumpsys ] && [ \"${3:-}\" = activity ]; then\n"
                "  cat \"$FAKE_ACTIVITY\"\n"
                "  exit 0\n"
                "fi\n"
                "exit 0\n",
                encoding="utf-8",
            )
            adb.chmod(0o755)

            runner = root / "run.sh"
            runner.write_text(
                "#!/usr/bin/env bash\nset -euo pipefail\n"
                f"WORK={str(work)!r}\n"
                + current_state_fn
                + "current_state\n",
                encoding="utf-8",
            )
            runner.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = str(fakebin) + os.pathsep + env.get("PATH", "")
            env["FAKE_LOG"] = str(fake_log)
            env["FAKE_ACTIVITY"] = str(fake_activity)
            cp = subprocess.run(
                [str(runner)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                check=True,
            )
            return cp.stdout.strip()

    def test_resumed_admob_interstitial_is_classified_as_ad_overlay(self):
        state = self.run_state(
            "",
            "mResumedActivity: ActivityRecord{abc u0 com.newstargames.newstarsoccer/com.google.android.gms.ads.AdActivity t42}\n",
        )
        self.assertEqual(state, "ad")

    def test_stale_admob_history_does_not_mask_resumed_monkey_game(self):
        state = self.run_state(
            "I/[Monkey]( 4445): SETTING ACTIVE: gamemenu\nI/[Monkey]( 4445): SetActive: gamemenu\n",
            "mResumedActivity: ActivityRecord{aaa u0 com.newstargames.newstarsoccer/.MonkeyGame t41}\n"
            "* Hist #1: ActivityRecord{bbb u0 com.newstargames.newstarsoccer/com.google.android.gms.ads.AdActivity t41}\n",
        )
        self.assertEqual(state, "gamemenu")


if __name__ == "__main__":
    unittest.main()
