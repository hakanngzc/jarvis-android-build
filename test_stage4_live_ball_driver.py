import importlib.util
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


def load_module(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_rgb_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        import binascii
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', binascii.crc32(kind + payload) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw))
    png += chunk(b'IEND', b'')
    path.write_bytes(png)


class Stage4LiveBallDriverTests(unittest.TestCase):
    def test_frame_validator_accepts_complete_png(self):
        validator = load_module('stage4_tools/validate_frame_png.py', 'validate_frame_png_ok')
        width, height = 32, 32
        pixels = bytearray(width * height * 3)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'complete.png'
            write_rgb_png(p, width, height, pixels)
            self.assertEqual((True, None), validator.validate_frame(p))

    def test_frame_validator_rejects_truncated_png(self):
        validator = load_module('stage4_tools/validate_frame_png.py', 'validate_frame_png_truncated')
        width, height = 32, 32
        pixels = bytearray(width * height * 3)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'truncated.png'
            write_rgb_png(p, width, height, pixels)
            data = p.read_bytes()
            p.write_bytes(data[:len(data) // 2])
            ok, error = validator.validate_frame(p)
            self.assertFalse(ok)
            self.assertTrue(error)

    def test_detector_finds_dense_green_active_ball_marker(self):
        detector = load_module('stage4_tools/find_live_ball.py', 'find_live_ball')
        width, height = 240, 320
        pixels = bytearray(width * height * 3)
        for y in range(125, 185):
            for x in range(70, 130):
                if x < 82 or x >= 118 or y < 137 or y >= 173:
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes((0, 72, 0))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'frame.png'
            write_rgb_png(p, width, height, pixels)
            self.assertEqual((100, 154), detector.find_live_ball(p))

    def test_detector_accepts_dim_grey_green_marker_seen_in_run185(self):
        detector = load_module('stage4_tools/find_live_ball.py', 'find_live_ball_run185_colour')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        # Run185 rendered the active ring around RGB (21..31, 60..100, 21..31),
        # which is greener than the pitch but not as saturated as earlier rings.
        for y in range(300, 380):
            for x in range(120, 200):
                if x < 136 or x >= 184 or y < 316 or y >= 364:
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes((27, 63, 27))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'run185-dim-marker.png'
            write_rgb_png(p, width, height, pixels)
            self.assertEqual((160, 340), detector.find_live_ball(p))

    def test_detector_ignores_disconnected_green_pitch_distractors(self):
        detector = load_module('stage4_tools/find_live_ball.py', 'find_live_ball_components')
        width, height = 360, 320
        pixels = bytearray(width * height * 3)
        for y in range(125, 185):
            for x in range(50, 110):
                if x < 62 or x >= 98 or y < 137 or y >= 173:
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes((0, 72, 0))
        for x in range(300, 360):
            i = (100 * width + x) * 3
            pixels[i:i + 3] = bytes((0, 72, 0))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'frame-with-distractor.png'
            write_rgb_png(p, width, height, pixels)
            self.assertEqual((80, 154), detector.find_live_ball(p))

    def test_detector_rejects_frame_without_active_marker(self):
        detector = load_module('stage4_tools/find_live_ball.py', 'find_live_ball_empty')
        width, height = 240, 320
        pixels = bytearray(width * height * 3)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'frame.png'
            write_rgb_png(p, width, height, pixels)
            self.assertIsNone(detector.find_live_ball(p))

    def test_kick_ball_detector_finds_large_neutral_ball(self):
        detector = load_module('stage4_tools/find_kick_ball.py', 'find_kick_ball')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        for y in range(360, 520):
            for x in range(100, 260):
                i = (y * width + x) * 3
                pixels[i:i + 3] = bytes((238, 238, 238))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'kick.png'
            write_rgb_png(p, width, height, pixels)
            result = detector.find_kick_ball(p)
            self.assertIsNotNone(result)
            x, y = result
            self.assertLessEqual(abs(x - 180), 45)
            self.assertLessEqual(abs(y - 440), 55)

    def test_kick_ball_detector_rejects_halftime_team_circle(self):
        detector = load_module('stage4_tools/find_kick_ball.py', 'find_kick_ball_halftime')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        for y in range(230, 390):
            for x in range(100, 260):
                i = (y * width + x) * 3
                pixels[i:i + 3] = bytes((238, 238, 238))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'halftime-team-circle.png'
            write_rgb_png(p, width, height, pixels)
            self.assertIsNone(detector.find_kick_ball(p))

    def test_compact_kick_ball_ignores_run185_lower_sponsor_strip(self):
        detector = load_module('stage4_tools/find_kick_ball.py', 'find_kick_ball_run185_strip')
        width, height = 360, 640
        bright = bytearray(width * height)
        # Run170 real compact ball band: ~74% screen height.
        for y in range(465, 485):
            for x in range(160, 180):
                bright[y * width + x] = 1
        # Run185 false positive sponsor/tribune text: ~81% screen height and
        # denser/larger than the real ball, so the old 0.88 lower bound won.
        for y in range(520, 545):
            for x in range(120, 145):
                bright[y * width + x] = 1
        self.assertEqual((170, 474), detector._find_compact_field_ball(width, height, bright))

    def test_match_resume_detector_finds_lower_right_play_ball(self):
        detector = load_module('stage4_tools/find_match_resume.py', 'find_match_resume')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        for y in range(470, 555):
            for x in range(270, 355):
                i = (y * width + x) * 3
                pixels[i:i + 3] = bytes((230, 230, 230))
        for y in range(505, 550):
            for x in range(300, 355):
                i = (y * width + x) * 3
                pixels[i:i + 3] = bytes((30, 190, 20))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'resume.png'
            write_rgb_png(p, width, height, pixels)
            self.assertEqual((311, 520), detector.find_match_resume(p))

    def test_live_input_hardener_replaces_blind_swipes_with_rendered_ball_swipe(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'prepare_stage4_live_input')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)
        self.assertIn('stage4_tools/find_live_ball.py', prepared)
        self.assertIn('stage4_tools/find_kick_ball.py', prepared)
        self.assertIn('stage4_tools/find_match_resume.py', prepared)
        self.assertIn('input touchscreen swipe "$x" "$y"', prepared)
        self.assertIn('input touchscreen tap "$x" "$y"', prepared)
        self.assertIn('drive_live_chance "$cycle" "$elapsed"', prepared)
        self.assertLess(
            prepared.index('stage4_tools/find_match_resume.py'),
            prepared.index('stage4_tools/find_kick_ball.py'),
        )
        self.assertNotIn('swipe_logical 320 700 320 250 420', prepared)
        self.assertNotIn('swipe_logical 260 690 460 280 380', prepared)
        self.assertNotIn('swipe_logical 380 690 180 280 380', prepared)
        self.assertNotIn('m_Simulate', prepared)
        self.assertNotIn('m_skipMatches', prepared)

    def test_live_input_hardener_validates_atomic_screenshot_before_detectors(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'prepare_stage4_live_input_frame_retry')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)
        self.assertIn('capture_valid_live_frame(){', prepared)
        self.assertIn('local final="$1" tmp attempt', prepared)
        self.assertIn('tmp="${final}.tmp"', prepared)
        self.assertNotIn('local final="$1" tmp="${final}.tmp"', prepared)
        self.assertLess(prepared.index('local final="$1" tmp attempt'), prepared.index('tmp="${final}.tmp"'))
        self.assertIn('for attempt in 1 2 3', prepared)
        self.assertIn('timeout 8s adb exec-out screencap -p > "$tmp"', prepared)
        self.assertIn('stage4_tools/validate_frame_png.py "$tmp"', prepared)
        self.assertIn('mv -f "$tmp" "$final"', prepared)
        self.assertIn('valid live frame unavailable', prepared)
        capture = prepared.index('capture_valid_live_frame "$frame"')
        resume = prepared.index('stage4_tools/find_match_resume.py', capture)
        self.assertLess(capture, resume)
        self.assertNotIn('adb exec-out screencap -p > "$frame"', prepared)

    def test_live_input_hardener_dismisses_only_foreground_admob_interstitial_before_navigation(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'prepare_stage4_live_input_ad_guard')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)
        self.assertIn('com.newstargames.newstarsoccer/com.google.android.gms.ads.AdActivity', prepared)
        self.assertIn('dismiss_interstitial_if_present "$step"', prepared)
        self.assertIn('adb shell input keyevent 4', prepared)
        self.assertIn('adb shell wm size', prepared)
        self.assertIn('w * 958 / 1000', prepared)
        self.assertIn('h * 35 / 1000', prepared)
        nav_guard = prepared.index('dismiss_interstitial_if_present "$step"')
        nav_clear = prepared.index('clear_log', nav_guard)
        self.assertLess(nav_guard, nav_clear)
        self.assertNotIn('m_Simulate', prepared)
        self.assertNotIn('m_skipMatches', prepared)

    def test_workflow_applies_live_ball_driver_after_prematch_gate(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        prematch = 'stage4_tools/prepare_stage4_prematch.py'
        live = 'stage4_tools/prepare_stage4_live_input.py'
        self.assertIn(prematch, text)
        self.assertIn(live, text)
        self.assertLess(text.index(prematch), text.index(live))
        self.assertIn('stage4-natural-gate.live.sh', text)
        self.assertIn('bash "$RUNNER_TEMP/stage4-natural-gate.live.sh"', text)
        self.assertIn('stage4_tools/find_kick_ball.py', text)
        self.assertIn('stage4_tools/find_match_resume.py', text)
        self.assertIn('stage4_tools/validate_frame_png.py', text)


if __name__ == '__main__':
    unittest.main()
