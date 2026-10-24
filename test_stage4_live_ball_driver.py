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
            self.assertEqual((100, 155), detector.find_live_ball(p))

    def test_detector_rejects_frame_without_active_marker(self):
        detector = load_module('stage4_tools/find_live_ball.py', 'find_live_ball_empty')
        width, height = 240, 320
        pixels = bytearray(width * height * 3)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'frame.png'
            write_rgb_png(p, width, height, pixels)
            self.assertIsNone(detector.find_live_ball(p))

    def test_live_input_hardener_replaces_blind_swipes_with_rendered_ball_swipe(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'prepare_stage4_live_input')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = hardener.harden(source)
        self.assertIn('stage4_tools/find_live_ball.py', prepared)
        self.assertIn('input touchscreen swipe "$x" "$y"', prepared)
        self.assertIn('drive_live_chance "$cycle" "$elapsed"', prepared)
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


if __name__ == '__main__':
    unittest.main()
