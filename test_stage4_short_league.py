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


class Stage4ShortLeagueTests(unittest.TestCase):
    def test_picker_detector_finds_first_rendered_albania_row(self):
        detector = load_module('stage4_tools/find_league_picker.py', 'find_league_picker_synthetic')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        centers = []
        for y0 in (125, 175, 225, 275, 325, 375):
            x0, x1 = 80, 280
            y1 = y0 + 30
            centers.append(((x0 + x1 - 1) // 2, (y0 + y1 - 1) // 2))
            for y in range(y0, y1):
                for x in range(x0, x1):
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes((30, 180, 20))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'picker.png'
            write_rgb_png(p, width, height, pixels)
            x, y = detector.find_albania_row(p)
            expected_x, expected_y = centers[0]
            self.assertLessEqual(abs(x - expected_x), 2)
            self.assertLessEqual(abs(y - expected_y), 2)

    def test_picker_detector_rejects_closed_screen_shape(self):
        detector = load_module('stage4_tools/find_league_picker.py', 'find_league_picker_closed')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        for y0 in (180, 280, 380):
            for y in range(y0, y0 + 45):
                for x in range(20, 340):
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes((30, 180, 20))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'closed.png'
            write_rgb_png(p, width, height, pixels)
            self.assertIsNone(detector.find_albania_row(p))

    def test_preparer_selects_rendered_albania_and_requires_viable_trial_clubs(self):
        module = load_module('stage4_tools/prepare_stage4_short_league.py', 'prepare_stage4_short_league')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('stage4_tools/find_league_picker.py', prepared)
        self.assertIn('short-league Albania stock row accepted', prepared)
        self.assertIn('continue_after_albania_stock_league(){', prepared)
        self.assertIn('List of prospective clubs size:', prepared)
        self.assertIn("grep -qE 'List of prospective clubs size:[[:space:]]*[1-9][0-9]*'", prepared)
        self.assertIn('short-league Albania produced viable prospective clubs', prepared)
        self.assertNotIn('short-league Andorra stock row accepted', prepared)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_preparer_retries_proven_profile_next_after_albania_selection(self):
        module = load_module('stage4_tools/prepare_stage4_short_league.py', 'prepare_stage4_short_league_next')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('for attempt in 1 2 3', prepared)
        self.assertIn('input touchscreen tap 940 1830', prepared)
        self.assertIn('input touchscreen swipe 940 1830 940 1830 220', prepared)
        self.assertIn('continue_after_albania_stock_league || exit 218', prepared)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_workflow_applies_short_league_before_prematch(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        short = 'stage4_tools/prepare_stage4_short_league.py'
        prematch = 'stage4_tools/prepare_stage4_prematch.py'
        self.assertIn(short, text)
        self.assertIn('stage4_tools/find_league_picker.py', text)
        self.assertIn(prematch, text)
        self.assertLess(text.index(short), text.index(prematch))
        self.assertIn('stage4-natural-gate.shortleague.sh', text)


if __name__ == '__main__':
    unittest.main()
