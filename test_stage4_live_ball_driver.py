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
        # Run169 reached the real 90' Full Time screen, where the lower-right
        # Continue control also resembles a large football. Resume/continue
        # must be classified before the generic kick-ball detector.
        self.assertLess(
            prepared.index('stage4_tools/find_match_resume.py'),
            prepared.index('stage4_tools/find_kick_ball.py'),
        )
        self.assertNotIn('swipe_logical 320 700 320 250 420', prepared)
        self.assertNotIn('swipe_logical 260 690 460 280 380', prepared)
        self.assertNotIn('swipe_logical 380 690 180 280 380', prepared)
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


if __name__ == '__main__':
    unittest.main()
