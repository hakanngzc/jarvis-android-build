import json
import tempfile
import unittest
from pathlib import Path

from production_logo_pipeline import (
    build_style_overrides,
    build_symbol_records,
    load_manifest,
    render_shield_extension,
)


class ProductionLogoPipelineTests(unittest.TestCase):
    def _manifest(self):
        return {
            "version": 1,
            "cell_size": 128,
            "clubs": [
                {"club_id": 3141, "style": 16, "symbol": "REBORNClub3141", "asset": "logos/3141.png"},
                {"club_id": 3157, "style": 17, "symbol": "REBORNClub3157", "asset": "logos/3157.png"},
                {"club_id": 3163, "style": 18, "symbol": "REBORNClub3163", "asset": "logos/3163.png"},
            ],
        }

    def test_manifest_drives_arbitrary_number_of_club_overrides(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest_path = root / "logos.json"
            for club_id in (3141, 3157, 3163):
                p = root / "logos" / f"{club_id}.png"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"placeholder")
            manifest_path.write_text(json.dumps(self._manifest()), encoding="utf-8")
            manifest = load_manifest(manifest_path, require_assets=True)

        self.assertEqual(build_style_overrides(manifest), {3141: 16, 3157: 17, 3163: 18})
        records = build_symbol_records(manifest, atlas_width=384, atlas_height=128)
        self.assertEqual([r[0] for r in records], ["REBORNClub3141", "REBORNClub3157", "REBORNClub3163"])
        self.assertEqual(records[0][1], [0.0, 0.0, 1/3, 1.0])
        self.assertEqual(records[2][1], [2/3, 0.0, 1.0, 1.0])

    def test_rejects_duplicate_ids_styles_symbols_and_stock_style_range(self):
        bad_cases = []
        base = self._manifest()

        dup_id = json.loads(json.dumps(base))
        dup_id["clubs"][1]["club_id"] = 3141
        bad_cases.append(dup_id)

        dup_style = json.loads(json.dumps(base))
        dup_style["clubs"][1]["style"] = 16
        bad_cases.append(dup_style)

        dup_symbol = json.loads(json.dumps(base))
        dup_symbol["clubs"][1]["symbol"] = "REBORNClub3141"
        bad_cases.append(dup_symbol)

        stock_style = json.loads(json.dumps(base))
        stock_style["clubs"][1]["style"] = 15
        bad_cases.append(stock_style)

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for idx, payload in enumerate(bad_cases):
                path = root / f"bad-{idx}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.subTest(idx=idx):
                    with self.assertRaises(ValueError):
                        load_manifest(path, require_assets=False)

    def test_shield_extension_is_data_driven_and_has_no_test_overlay(self):
        extension = render_shield_extension(self._manifest())
        self.assertEqual(extension.count("Selector(MatchColours,BadgeStyle1)"), 1)
        self.assertEqual(extension.count("Selector(MatchColours,BadgeStyle2)"), 1)
        for symbol in ("REBORNClub3141", "REBORNClub3157", "REBORNClub3163"):
            self.assertEqual(extension.count(f"Draw:({symbol},"), 2)
        # A sibling selector contributes 16 blanks before custom style 16.
        first_selector = extension.split("Selector(MatchColours,BadgeStyle2)", 1)[0]
        self.assertGreaterEqual(first_selector.count("Rect:(0,0,0,0)"), 17)
        self.assertNotIn("STAGE6_TEST_ONLY_LOGO_PROOF", extension)
        self.assertNotIn("mainmenu.uis", extension)
        self.assertNotIn("onboarding", extension.lower())

    def test_manifest_output_is_deterministic(self):
        one = render_shield_extension(self._manifest())
        two = render_shield_extension(json.loads(json.dumps(self._manifest())))
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
