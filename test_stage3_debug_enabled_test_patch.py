#!/usr/bin/env python3
import importlib.util
import pathlib
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent
PATCHER = ROOT / 'stage3_tools' / 'patch_debug_enabled_test.py'


class DebugEnabledTestPatchTests(unittest.TestCase):
    def load_module(self):
        spec = importlib.util.spec_from_file_location('patch_debug_enabled_test', PATCHER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_changes_only_exact_debug_default(self):
        mod = self.load_module()
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            src = td / 'in.apk'
            dst = td / 'out.apk'
            tweak = (
                b'Category:(Debug) NOLOCAL\n'
                b'\tVar:(DebugEnabled,Debug Buttons Enabled,0,1)\n'
                b'\tVar:(GoalAreas,Showed Goal Areas,0,1)\n'
                b'EndCategory\n'
            )
            with zipfile.ZipFile(src, 'w') as z:
                z.writestr('assets/monkey/Tweaks/TweakValues.txt', tweak)
                z.writestr('assets/keep.bin', b'unchanged')
            mod.patch(src, dst)
            with zipfile.ZipFile(dst) as z:
                out = z.read('assets/monkey/Tweaks/TweakValues.txt')
                self.assertIn(b'Var:(DebugEnabled,Debug Buttons Enabled,1,1)', out)
                self.assertNotIn(b'Var:(DebugEnabled,Debug Buttons Enabled,0,1)', out)
                self.assertEqual(z.read('assets/keep.bin'), b'unchanged')

    def test_refuses_ambiguous_source(self):
        mod = self.load_module()
        with tempfile.TemporaryDirectory() as td:
            td = pathlib.Path(td)
            src = td / 'in.apk'
            dst = td / 'out.apk'
            with zipfile.ZipFile(src, 'w') as z:
                z.writestr('assets/monkey/Tweaks/TweakValues.txt', b'Category:(Debug)\nEndCategory\n')
            with self.assertRaises(SystemExit):
                mod.patch(src, dst)


if __name__ == '__main__':
    unittest.main()
