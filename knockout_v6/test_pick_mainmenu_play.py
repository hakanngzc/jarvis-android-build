import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw
from knockout_v6.pick_mainmenu_play import pick


class MainMenuPlayPickerV6Tests(unittest.TestCase):
    def _make(self, bands):
        td = tempfile.TemporaryDirectory()
        path = Path(td.name) / 'menu.png'
        image = Image.new('RGB', (1080, 2280), (20, 20, 20))
        draw = ImageDraw.Draw(image)
        for box in bands:
            draw.rectangle(box, fill=(74, 180, 13))
        image.save(path)
        return td, path

    def test_rejects_single_slide_in_play_band(self):
        td, path = self._make([(180, 1328, 670, 1434)])
        with td, self.assertRaises(ValueError):
            pick(path)

    def test_accepts_settled_three_button_menu_and_picks_play(self):
        td, path = self._make([
            (390, 1328, 990, 1434),
            (350, 1482, 930, 1588),
            (300, 1632, 850, 1740),
        ])
        with td:
            x, y, groups = pick(path)
            self.assertEqual(len(groups), 3)
            self.assertGreater(x, 600)
            self.assertTrue(1328 <= y <= 1434)

    def test_rejects_frame_without_action_bands(self):
        td, path = self._make([])
        with td, self.assertRaises(ValueError):
            pick(path)


if __name__ == '__main__':
    unittest.main()
