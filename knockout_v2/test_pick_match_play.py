import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

MODULE = Path(__file__).with_name('pick_match_play.py')


class MatchPlayPickerTests(unittest.TestCase):
    def load(self):
        spec = importlib.util.spec_from_file_location('pick_match_play', MODULE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_picks_bottom_right_green_play_label(self):
        mod = self.load()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'match.png'
            image = Image.new('RGB', (1080, 2280), (30, 30, 30))
            draw = ImageDraw.Draw(image)
            draw.rectangle((870, 1815, 1015, 1871), fill=(80, 184, 18))
            image.save(path)
            x, y, count = mod.pick(path)
            self.assertGreaterEqual(count, 300)
            self.assertTrue(900 <= x <= 980)
            self.assertTrue(1815 <= y <= 1871)

    def test_rejects_frame_without_visible_play_control(self):
        mod = self.load()
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'overlay.png'
            Image.new('RGB', (1080, 2280), (30, 30, 30)).save(path)
            with self.assertRaises(SystemExit):
                mod.pick(path)


if __name__ == '__main__':
    unittest.main()
