import importlib.util
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


def load_module(path_str: str, name: str):
    path = Path(path_str)
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_rgb_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        import binascii
        return struct.pack('>I', len(payload)) + kind + payload + struct.pack('>I', binascii.crc32(kind + payload) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    png = b'\x89PNG\r\n\x1a\n'
    png += chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
    png += chunk(b'IDAT', zlib.compress(raw))
    png += chunk(b'IEND', b'')
    path.write_bytes(png)


class Stage4EventNavigationTests(unittest.TestCase):
    def test_dilemma_detector_selects_upper_gold_choice(self):
        detector = load_module('stage4_tools/find_dilemma_choice.py', 'find_dilemma_choice_synthetic')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        for y0 in (260, 430):
            for y in range(y0, y0 + 26):
                for x in range(75, 245):
                    i = (y * width + x) * 3
                    pixels[i:i + 3] = bytes((245, 190, 20))
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'dilemma.png'
            write_rgb_png(p, width, height, pixels)
            x, y = detector.find_dilemma_choice(p)
            self.assertLessEqual(abs(x - 159), 3)
            self.assertLessEqual(abs(y - 272), 3)

    def test_dilemma_detector_rejects_screen_without_choice_bars(self):
        detector = load_module('stage4_tools/find_dilemma_choice.py', 'find_dilemma_choice_empty')
        width, height = 360, 640
        pixels = bytearray(width * height * 3)
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / 'empty.png'
            write_rgb_png(p, width, height, pixels)
            self.assertIsNone(detector.find_dilemma_choice(p))

    def test_event_preparer_classifies_splash_before_generic_message_and_handles_both_loops(self):
        module = load_module('stage4_tools/prepare_stage4_event_navigation.py', 'prepare_stage4_event_navigation')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('*dilemma*) echo dilemma;; *splashmessage*) echo splashmessage;;', prepared)
        self.assertLess(prepared.index('*splashmessage*) echo splashmessage;;'), prepared.index('*message*) echo message;;'))
        self.assertIn('resolve_stage4_dilemma(){', prepared)
        self.assertIn('stage4_tools/find_dilemma_choice.py', prepared)
        self.assertIn('dilemma|splashmessage) resolve_stage4_dilemma || return 1;;', prepared)
        self.assertEqual(prepared.count('dilemma|splashmessage) resolve_stage4_dilemma || return 1;;'), 2)
        self.assertIn('stock dilemma choice accepted', prepared)
        self.assertIn('for attempt in 1 2 3 4', prepared)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_event_preparer_uses_stock_webpage_footer_ok_in_both_navigation_loops(self):
        module = load_module('stage4_tools/prepare_stage4_event_navigation.py', 'prepare_stage4_event_navigation_webpage')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertEqual(prepared.count('webpage) press_footer_ok 2;;'), 2)
        self.assertNotIn('message|webpage|startransition) press_message_accept 2;;', prepared)

    def test_event_preparer_classifies_and_dismisses_stock_fake_interstitial_in_both_loops(self):
        module = load_module('stage4_tools/prepare_stage4_event_navigation.py', 'prepare_stage4_event_navigation_interstitial')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        self.assertIn('*fake-interstitial*) echo fakeinterstitial;;', prepared)
        self.assertIn('dismiss_stage4_fake_interstitial(){', prepared)
        self.assertIn('adb shell input keyevent 4', prepared)
        self.assertEqual(prepared.count('fakeinterstitial) dismiss_stage4_fake_interstitial || return 1;;'), 2)
        for forbidden in ('m_sdate = 365', 'm_sdate=365', 'p_NewSeason(', 'm_skipMatches', 'm_Simulate'):
            self.assertNotIn(forbidden, prepared)

    def test_event_preparer_retains_last_verified_state_when_no_transition_is_published(self):
        module = load_module('stage4_tools/prepare_stage4_event_navigation.py', 'prepare_stage4_event_navigation_state')
        source = Path('stage4_natural_season_gate.sh').read_text(encoding='utf-8')
        prepared = module.harden(source)
        # Run231 proved matchstats.dismissanim can consume the first tap without
        # changing screens. A missing new SetActive marker must not be treated as
        # permission to press an unrelated footer control.
        self.assertIn('navigate step $step no published transition; retaining $state', prepared)
        self.assertIn('cycle $cycle postmatch no published transition; retaining $state', prepared)
        self.assertNotIn('[ "$state" = unknown ] && { press_footer_ok 1; state="$(latest_state)"; }', prepared)
        self.assertIn('next_state="$(latest_state)"', prepared)

    def test_workflow_applies_event_navigation_before_prematch_and_live_hardening(self):
        text = Path('.github/workflows/nss-stage4-season-runtime.yml').read_text(encoding='utf-8')
        event = 'stage4_tools/prepare_stage4_event_navigation.py'
        prematch = 'stage4_tools/prepare_stage4_prematch.py'
        live = 'stage4_tools/prepare_stage4_live_input.py'
        self.assertIn(event, text)
        self.assertIn('stage4_tools/find_dilemma_choice.py', text)
        self.assertLess(text.index(event), text.index(prematch))
        self.assertLess(text.index(event), text.index(live))
        self.assertIn('stage4-natural-gate.events.sh', text)


if __name__ == '__main__':
    unittest.main()
