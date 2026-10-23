import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from knockout_v5.pick_mainmenu_play import pick


class MainMenuPlayPickerV5Tests(unittest.TestCase):
    def test_accepts_single_wide_play_band(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'single-play.png'
            image = Image.new('RGB', (1080, 2280), (20, 20, 20))
            ImageDraw.Draw(image).rectangle((180, 1328, 670, 1434), fill=(74, 180, 13))
            image.save(path)
            x, y, groups = pick(path)
            self.assertEqual(len(groups), 1)
            self.assertTrue(350 <= x <= 550)
            self.assertTrue(1328 <= y <= 1434)

    def test_rejects_frame_without_action_band(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'none.png'
            Image.new('RGB', (1080, 2280), (20, 20, 20)).save(path)
            with self.assertRaises(SystemExit):
                pick(path)


if __name__ == '__main__':
    unittest.main()
