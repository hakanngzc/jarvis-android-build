#!/usr/bin/env python3
import unittest
from stage8_tools.patch_stage8_age_unlock import build_age_units, TARGET_AGE

class Stage8AgeUnlockTests(unittest.TestCase):
    def test_age_probe_returns_later_career_age(self):
        self.assertEqual(TARGET_AGE,18)
        self.assertEqual(build_age_units(TARGET_AGE),[0x0013,18,0x000f])

    def test_rejects_out_of_range_age(self):
        with self.assertRaises(ValueError): build_age_units(40000)

if __name__=='__main__':unittest.main()
