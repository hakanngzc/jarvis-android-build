#!/usr/bin/env python3
import os
import re
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class Stage3WeeklyReviewStateTest(unittest.TestCase):
    def test_weekly_review_internal_phase_is_classified_as_matchreview(self):
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
            fake_log = root / "weekly.log"
            fake_log.write_text(
                "I/[Monkey]( 4358): USE player.matchReviewBuxAwarded: 0\n"
                "I/[Monkey]( 4358): Award Currency 1\n",
                encoding="utf-8",
            )
            adb = fakebin / "adb"
            adb.write_text(
                "#!/usr/bin/env bash\n"
                "if [ \"${1:-}\" = logcat ]; then cat \"$FAKE_LOG\"; exit 0; fi\n"
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
            cp = subprocess.run(
                [str(runner)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                check=True,
            )
            self.assertEqual(cp.stdout.strip(), "matchreview")


if __name__ == "__main__":
    unittest.main()
