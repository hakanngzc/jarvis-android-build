import unittest
from refine_catchall_owners import choose_candidate, structural_role

class RefineOwnersTest(unittest.TestCase):
    def test_choose_candidate_requires_margin(self):
        self.assertEqual(choose_candidate({'match_engine': 8, 'utility_core': 2}), ('match_engine','high'))
        self.assertEqual(choose_candidate({'match_engine': 3, 'utility_core': 2}), ('match_engine','medium'))
        self.assertEqual(choose_candidate({'match_engine': 2, 'utility_core': 2}), ('ambiguous','none'))
    def test_structural_helpers_are_not_misrepresented_as_domain_owners(self):
        self.assertEqual(structural_role('c_Enumerator24'), 'collection_iterator')
        self.assertEqual(structural_role('c_Node50'), 'collection_node')
        self.assertEqual(structural_role('c_SceneFactory'), 'factory')
        self.assertEqual(structural_role('c_ActionAfterPlay'), 'domain_object')

if __name__ == '__main__': unittest.main()
