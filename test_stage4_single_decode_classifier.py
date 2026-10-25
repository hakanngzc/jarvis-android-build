import importlib.util
import tempfile
import unittest
from pathlib import Path

from test_stage4_live_ball_driver import write_rgb_png


def load_classifier():
    path = Path('stage4_tools/classify_live_frame.py')
    spec = importlib.util.spec_from_file_location('classify_live_frame_test', path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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
