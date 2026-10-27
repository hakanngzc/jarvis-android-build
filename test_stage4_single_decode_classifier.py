import importlib.util
import tempfile
import unittest
from pathlib import Path

from test_stage4_live_ball_driver import write_rgb_png


def load_module(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_classifier():
    return load_module('stage4_tools/classify_live_frame.py', 'classify_live_frame_test')


class Stage4SingleDecodeClassifierTests(unittest.TestCase):
    def test_live_marker_classification(self):
        classifier = load_classifier()
        w, h = 360, 640
        pixels = bytearray(w * h * 3)
        for y in range(300, 380):
            for x in range(120, 200):
                if x < 136 or x >= 184 or y < 316 or y >= 364:
                    i = (y * w + x) * 3
                    pixels[i:i + 3] = bytes((27, 63, 27))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'live.png'
            write_rgb_png(p, w, h, pixels)
            self.assertEqual(('live', 160, 340), classifier.classify_live_frame(p))

    def test_resume_has_priority(self):
        classifier = load_classifier()
        w, h = 360, 640
        pixels = bytearray(w * h * 3)
        for y in range(470, 555):
            for x in range(270, 355):
                i = (y * w + x) * 3
                pixels[i:i + 3] = bytes((230, 230, 230))
        for y in range(505, 550):
            for x in range(300, 355):
                i = (y * w + x) * 3
                pixels[i:i + 3] = bytes((30, 190, 20))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'resume.png'
            write_rgb_png(p, w, h, pixels)
            self.assertEqual(('resume', 311, 520), classifier.classify_live_frame(p))

    def test_run310_stock_match_tutorial_panel_is_classified_before_passive_wait(self):
        classifier = load_classifier()
        w, h = 360, 640
        pixels = bytearray(w * h * 3)
        # Run 310 artifact timed out at Full Time with the stock grey Tutorial
        # callout still covering the match surface. Model the large neutral
        # central panel rather than text/OCR so detection stays resolution-safe.
        for y in range(165, 405):
            for x in range(35, 275):
                i = (y * w + x) * 3
                pixels[i:i + 3] = bytes((96, 96, 96))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'tutorial.png'
            write_rgb_png(p, w, h, pixels)
            self.assertEqual(('tutorial', 180, 320), classifier.classify_live_frame(p))

    def test_run310_live_driver_advances_only_visually_confirmed_tutorial_overlay(self):
        hardener = load_module('stage4_tools/prepare_stage4_live_input.py', 'prepare_stage4_live_input_tutorial')
        prepared = hardener.harden(Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8'))
        self.assertIn('tutorial)', prepared)
        self.assertIn('cycle $cycle stock tutorial overlay', prepared)
        self.assertIn('adb shell input touchscreen tap "$x" "$y"', prepared)
        self.assertNotIn('m_Simulate', prepared)
        self.assertNotIn('m_skipMatches', prepared)

    def test_empty_frame_is_none(self):
        classifier = load_classifier()
        w, h = 240, 320
        pixels = bytearray(w * h * 3)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'empty.png'
            write_rgb_png(p, w, h, pixels)
            self.assertIsNone(classifier.classify_live_frame(p))


if __name__ == '__main__':
    unittest.main()
