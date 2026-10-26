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


class Stage4StockMatchSpeedTests(unittest.TestCase):
    def test_detector_classifies_stock_speed_icon_colours(self):
        detector = load_module('stage4_tools/find_match_speed.py', 'find_match_speed_synthetic')
        cases = (
            (1200, (255, 255, 29)),
            (800, (255, 108, 0)),
            (350, (254, 23, 23)),
        )
        for expected, rgb in cases:
            width, height = 360, 640
            pixels = bytearray(width * height * 3)
            for y in range(45, 62):
                for x in range(315, 332):
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes(rgb)
            with tempfile.TemporaryDirectory() as td:
                p = Path(td) / f'speed-{expected}.png'
                write_rgb_png(p, width, height, pixels)
                result = detector.find_match_speed(p)
                self.assertIsNotNone(result)
                speed, x, y = result
                self.assertEqual(expected, speed)
                self.assertTrue(315 <= x <= 331)
                self.assertTrue(45 <= y <= 61)

    def test_detector_rejects_frame_without_stock_speed_colour(self):
        detector = load_module('stage4_tools/find_match_speed.py', 'find_match_speed_empty')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'empty.png'
            write_rgb_png(p, width, height, pixels)
            self.assertIsNone(detector.find_match_speed(p))

    def test_composed_hardener_visually_drives_stock_time_button_to_350(self):
        live = load_module('stage4_tools/prepare_stage4_live_input.py', 'prepare_stage4_live_input_speed_base')
        speed = load_module('stage4_tools/prepare_stage4_match_speed.py', 'prepare_stage4_match_speed')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = speed.harden(live.harden(source))
        self.assertIn('set_fastest_stock_match_speed(){', prepared)
        self.assertIn('stage4_tools/find_match_speed.py', prepared)
        self.assertIn('[ "$speed" = 350 ]', prepared)
        self.assertIn('input touchscreen tap "$x" "$y"', prepared)
        self.assertIn('set_fastest_stock_match_speed "$cycle" || return 1', prepared)
        self.assertIn('stock MatchSpeed=350 verified', prepared)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_workflow_compiles_applies_and_runs_stock_speed_detector_tests(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        self.assertIn('stage4_tools/find_match_speed.py', text)
        self.assertIn('stage4_tools/prepare_stage4_match_speed.py', text)
        self.assertIn('test_stage4_match_speed.py', text)
        self.assertIn('stage4-natural-gate.speed.sh', text)
        self.assertLess(text.index('stage4_tools/prepare_stage4_live_input.py'), text.index('stage4_tools/prepare_stage4_match_speed.py'))
        self.assertLess(text.index('stage4_tools/prepare_stage4_match_speed.py'), text.index('stage4_tools/prepare_stage4_boundary_scope.py'))


if __name__ == '__main__':
    unittest.main()
