import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from patch_lifecycle_probe_v8 import SLOT_FINDER_REPLACEMENT, patch_slot_finder
from slot_target_geometry import detect_primary_slot_target


class SlotTargetGeometryTest(unittest.TestCase):
    def _synthetic_saveslot(self, path: Path, footer_only: bool = False) -> None:
        im = Image.new('RGB', (1080, 2280), (45, 55, 52))
        draw = ImageDraw.Draw(im)
        green = (46, 178, 8)
        if not footer_only:
            draw.rectangle((30, 760, 800, 860), fill=green)
            draw.rectangle((30, 1054, 790, 1154), fill=green)
            draw.rectangle((0, 1348, 705, 1448), fill=green)
        # Footer Tutorial/Google controls must never be mistaken for Save Slot 1.
        draw.rectangle((228, 1710, 400, 1975), fill=green)
        draw.rectangle((630, 1710, 805, 1975), fill=green)
        im.save(path)

    def test_primary_slot_target_chooses_first_career_button_not_footer(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'saveslot.png'
            self._synthetic_saveslot(src)
            x, y, bands = detect_primary_slot_target(src)
        self.assertGreaterEqual(len(bands), 3)
        self.assertGreater(x, 300)
        self.assertLess(x, 800)
        self.assertGreater(y, 700)
        self.assertLess(y, 950)

    def test_footer_only_image_is_rejected_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'footer-only.png'
            self._synthetic_saveslot(src, footer_only=True)
            with self.assertRaises(ValueError):
                detect_primary_slot_target(src)


class LifecyclePatchV8Test(unittest.TestCase):
    def test_replacement_uses_dedicated_slot_geometry_helper(self):
        self.assertIn('lifecycle/slot_target_geometry.py', SLOT_FINDER_REPLACEMENT)
        self.assertNotIn('palette=[', SLOT_FINDER_REPLACEMENT)

    def test_patch_refuses_missing_or_changed_v7_slot_finder(self):
        with self.assertRaises(ValueError):
            patch_slot_finder('find_slot0_target shape changed')


if __name__ == '__main__':
    unittest.main()
