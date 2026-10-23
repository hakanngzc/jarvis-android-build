import unittest

from knockout_v4.strip_redundant_emulator_probe import strip_redundant_emulator_probe

SAMPLE = '''before\n# The repository contract pins this exact Android Emulator build.\nemulator -version 2>&1 | tee "$RUNNER_TEMP/nss-stage3-emulator-version.txt"\ngrep -q 'build_id 16428233' "$RUNNER_TEMP/nss-stage3-emulator-version.txt"\n\nbash "$RUNTIME" "$MODE"\n'''


class StripRedundantEmulatorProbeTests(unittest.TestCase):
    def test_removes_only_redundant_probe(self):
        out = strip_redundant_emulator_probe(SAMPLE)
        self.assertNotIn('emulator -version', out)
        self.assertNotIn('nss-stage3-emulator-version.txt', out)
        self.assertIn('bash "$RUNTIME" "$MODE"', out)
        self.assertTrue(out.startswith('before\n'))

    def test_refuses_changed_source(self):
        with self.assertRaises(ValueError):
            strip_redundant_emulator_probe('bash "$RUNTIME" "$MODE"\n')


if __name__ == '__main__':
    unittest.main()
