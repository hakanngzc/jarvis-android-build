import io
import unittest
import zipfile
from pathlib import Path

from patch_preserve_egl_activity import patch_apk_bytes, rewrite_manifest_activity


class PreserveEglActivityPatchTest(unittest.TestCase):
    def test_rewrites_equal_length_activity_name_in_utf8_manifest(self):
        src=b'prefix com.newstargames.newstarsoccer.MonkeyGame suffix'
        out,count=rewrite_manifest_activity(src)
        self.assertEqual(count,1)
        self.assertIn(b'com.newstargames.newstarsoccer.RebornGame',out)
        self.assertEqual(len(src),len(out))

    def test_rewrites_equal_length_activity_name_in_utf16_manifest(self):
        src='prefix .MonkeyGame suffix'.encode('utf-16le')
        out,count=rewrite_manifest_activity(src)
        self.assertEqual(count,1)
        self.assertIn('.RebornGame'.encode('utf-16le'),out)
        self.assertEqual(len(src),len(out))

    def test_refuses_manifest_without_stock_activity_name(self):
        with self.assertRaises(ValueError):
            rewrite_manifest_activity(b'no stock activity here')

    def test_injects_new_dex_without_touching_existing_dex_payloads(self):
        src=io.BytesIO()
        with zipfile.ZipFile(src,'w') as z:
            z.writestr('AndroidManifest.xml',b'.MonkeyGame')
            z.writestr('classes.dex',b'dex-one')
            z.writestr('classes3.dex',b'dex-three')
            z.writestr('assets/x',b'asset')
        out,evidence=patch_apk_bytes(src.getvalue(),b'new-helper-dex')
        with zipfile.ZipFile(io.BytesIO(out)) as z:
            self.assertEqual(z.read('classes.dex'),b'dex-one')
            self.assertEqual(z.read('classes3.dex'),b'dex-three')
            self.assertEqual(z.read('assets/x'),b'asset')
            self.assertEqual(z.read('classes4.dex'),b'new-helper-dex')
            self.assertIn(b'.RebornGame',z.read('AndroidManifest.xml'))
        self.assertEqual(evidence['helper_dex_entry'],'classes4.dex')
        self.assertEqual(evidence['existing_dex_entries'],['classes.dex','classes3.dex'])
        self.assertEqual(evidence['manifest_replacements'],1)

    def test_refuses_existing_classes4_to_avoid_overwrite(self):
        src=io.BytesIO()
        with zipfile.ZipFile(src,'w') as z:
            z.writestr('AndroidManifest.xml',b'.MonkeyGame')
            z.writestr('classes4.dex',b'existing')
        with self.assertRaises(ValueError):
            patch_apk_bytes(src.getvalue(),b'helper')

    def test_activity_shim_preserves_stock_monkeygame_preferences_namespace(self):
        src=Path('java_shim/com/newstargames/newstarsoccer/RebornGame.java').read_text(encoding='utf-8')
        self.assertIn('SharedPreferences getPreferences(int mode)',src)
        self.assertIn('getSharedPreferences("MonkeyGame", mode)',src)


if __name__=='__main__':
    unittest.main()
