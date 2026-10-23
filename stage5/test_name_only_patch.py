import csv
import io
import unittest
import zipfile

from stage5.name_only_patch import patch_apk_bytes


ASSETS = {
    'assets/monkey/MyData/v2025/Clubs.txt': (
        'id\tshortname\ttla\tstrength\tnationid\tleagueid\tcontinentalcompid\tbteamof\n'
        '//meta\t\t\t\t\t\t\t\n'
        '10\tOld Club\tOLD\t50\t1\t100\t0\t0\n'
        '11\tOther Club\tOTH\t55\t1\t101\t100\t10\n'
    ),
    'assets/monkey/MyData/v2025/Nations.txt': (
        'id\tname\n'
        '1\tNation One\n'
        '2\tNation Two\n'
    ),
    'assets/monkey/MyData/v2025/Competitions.txt': (
        'id\tname\n'
        '100\tLeague One\n'
        '101\tLeague Two\n'
    ),
}


def build_apk() -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as z:
        for path, text in ASSETS.items():
            z.writestr(path, text)
        z.writestr('classes.dex', b'dex-bytes-unchanged')
    return out.getvalue()


def rows(apk: bytes, path: str):
    with zipfile.ZipFile(io.BytesIO(apk)) as z:
        text = z.read(path).decode('utf-8-sig')
    return list(csv.DictReader(io.StringIO(text), delimiter='\t'))


class NameOnlyPatchContractTests(unittest.TestCase):
    def test_suffixes_every_numeric_identity_name_but_preserves_ids_order_and_refs(self):
        before = build_apk()
        after, report = patch_apk_bytes(before, suffix='~')

        self.assertEqual(2, report['changed']['clubs'])
        self.assertEqual(2, report['changed']['nations'])
        self.assertEqual(2, report['changed']['competitions'])
        self.assertEqual(6, report['changed_total'])
        self.assertTrue(report['identity_contract_preserved'])
        self.assertTrue(report['persistent_references_preserved'])

        cb = rows(before, 'assets/monkey/MyData/v2025/Clubs.txt')
        ca = rows(after, 'assets/monkey/MyData/v2025/Clubs.txt')
        self.assertEqual([r['id'] for r in cb], [r['id'] for r in ca])
        self.assertEqual('//meta', ca[0]['id'])
        self.assertEqual('', ca[0]['shortname'])
        self.assertEqual('Old Club~', ca[1]['shortname'])
        self.assertEqual('Other Club~', ca[2]['shortname'])
        for col in ('nationid', 'leagueid', 'continentalcompid', 'bteamof'):
            self.assertEqual([r[col] for r in cb], [r[col] for r in ca])

        for path in (
            'assets/monkey/MyData/v2025/Nations.txt',
            'assets/monkey/MyData/v2025/Competitions.txt',
        ):
            rb = rows(before, path)
            ra = rows(after, path)
            self.assertEqual([r['id'] for r in rb], [r['id'] for r in ra])
            self.assertEqual([r['name'] + '~' for r in rb], [r['name'] for r in ra])

        with zipfile.ZipFile(io.BytesIO(after)) as z:
            self.assertEqual(b'dex-bytes-unchanged', z.read('classes.dex'))

    def test_rejects_control_characters_in_suffix(self):
        with self.assertRaisesRegex(ValueError, 'control separator'):
            patch_apk_bytes(build_apk(), suffix='\nBAD')


if __name__ == '__main__':
    unittest.main()
