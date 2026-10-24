import unittest

from patch_activity_super_lifecycle import rewrite_super_call


class ActivitySuperLifecyclePatchTest(unittest.TestCase):
    def test_rewrites_only_invoke_super_method_index(self):
        stock=[0x106f,23,0x0002,0x0154,0x1234,0x0054]
        out=rewrite_super_call(stock, resume_method_id=23, target_method_id=25)
        self.assertEqual(out,[0x106f,25,0x0002,0x0154,0x1234,0x0054])
        self.assertEqual([i for i,(a,b) in enumerate(zip(stock,out)) if a!=b],[1])

    def test_refuses_non_resume_super_call(self):
        with self.assertRaises(ValueError):
            rewrite_super_call([0x106f,22,0x0002,0x000e], resume_method_id=23, target_method_id=25)

    def test_refuses_changed_invoke_super_shape(self):
        with self.assertRaises(ValueError):
            rewrite_super_call([0x006e,23,0x0002,0x000e], resume_method_id=23, target_method_id=25)

    def test_refuses_method_ids_that_do_not_fit_dex_index(self):
        with self.assertRaises(ValueError):
            rewrite_super_call([0x106f,23,0x0002], resume_method_id=23, target_method_id=0x10000)


if __name__=='__main__':
    unittest.main()
