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
    def test_picker_detector_returns_first_visible_albania_candidate(self):
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

    def test_picker_detector_accepts_short_visible_page_for_first_row(self):
        detector = load_module('stage4_tools/find_league_picker.py', 'find_league_picker_partial')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        centers = []
        for y0 in (145, 205, 265):
            x0, x1 = 78, 282
            y1 = y0 + 28
            centers.append(((x0 + x1 - 1) // 2, (y0 + y1 - 1) // 2))
            for y in range(y0, y1):
                for x in range(x0, x1):
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes((35, 175, 25))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'partial.png'
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

    def test_preparer_selects_albania_without_scroll_and_requires_nation_2_plus_viable_clubs(self):
        module = load_module('stage4_tools/prepare_stage4_short_league.py', 'prepare_stage4_short_league')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertNotIn('for page in 1 2 3 4 5 6 7', prepared)
        self.assertIn('short-league Albania rendered row accepted', prepared)
        self.assertIn('continue_after_albania_stock_league(){', prepared)
        self.assertIn("GetProspectiveClubs for nation Id:[[:space:]]*2", prepared)
        self.assertIn("List of prospective clubs size:[[:space:]]*[1-9][0-9]*", prepared)
        self.assertIn('short-league Albania nation 2 produced viable prospective clubs', prepared)
        self.assertNotIn('short-league Argentina rendered row accepted', prepared)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_preparer_opens_league_picker_at_source_defined_pressable_center(self):
        module = load_module('stage4_tools/prepare_stage4_short_league.py', 'prepare_stage4_short_league_button_center')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        start = prepared.index('select_albania_stock_league(){')
        end = prepared.index('continue_after_albania_stock_league(){', start)
        selector = prepared[start:end]
        self.assertIn('press_logical 332 672 1', selector)
        self.assertNotIn('press_logical 64 630 1', selector)
        self.assertNotIn('press_logical 320 640 1', selector)

    def test_preparer_waits_for_open_modal_before_any_second_selector_press(self):
        module = load_module('stage4_tools/prepare_stage4_short_league.py', 'prepare_stage4_short_league_modal_wait')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        start = prepared.index('select_albania_stock_league(){')
        end = prepared.index('continue_after_albania_stock_league(){', start)
        selector = prepared[start:end]
        self.assertIn('for detect_attempt in 1 2 3 4', selector)
        self.assertIn('short-league Albania modal ready', selector)
        self.assertIn('modal_open=1', selector)
        self.assertIn('[ "$modal_open" -eq 1 ] || continue', selector)
        self.assertLess(selector.index('for detect_attempt in 1 2 3 4'), selector.index('adb shell input touchscreen tap "$x" "$y"'))
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, selector)

    def test_preparer_retries_stock_profile_next_after_albania_selection(self):
        module = load_module('stage4_tools/prepare_stage4_short_league.py', 'prepare_stage4_short_league_next')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('for attempt in 1 2 3', prepared)
        self.assertIn('input touchscreen tap 940 1830', prepared)
        self.assertIn('input touchscreen swipe 940 1830 940 1830 220', prepared)
        self.assertIn('continue_after_albania_stock_league || exit 218', prepared)

    def test_external_runner_retries_only_disposable_setup_failures(self):
        runner = Path('stage4_tools/run_stage4_natural_gate.sh').read_text(encoding='utf-8')
        self.assertIn('for setup_attempt in 1 2 3', runner)
        self.assertIn('218|219)', runner)
        self.assertIn('setup-only retry after rc=$rc', runner)
        self.assertIn('*) exit "$rc";;', runner)
        retry_case = runner[runner.index('case "$rc" in'):runner.index('esac', runner.index('case "$rc" in'))]
        self.assertNotIn('220', retry_case)
        self.assertNotIn('221', retry_case)

    def test_workflow_invokes_external_setup_retry_runner_as_single_command(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        self.assertIn('bash stage4_tools/run_stage4_natural_gate.sh "$RUNNER_TEMP/stage4-natural-gate.live.sh"', text)
        self.assertNotIn('for setup_attempt in 1 2 3', text)

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
