import unittest
from refine_catchall_owners import choose_candidate, structural_role, trace_owner_candidate, duty_family

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

    def test_duty_family_uses_exact_technical_families_without_claiming_subsystem(self):
        self.assertEqual(duty_family('c_EX_Gel_Alpha', 'domain_object'), 'expression_engine')
        self.assertEqual(duty_family('c_GelEmitter', 'domain_object'), 'gel_runtime')
        self.assertEqual(duty_family('c_GLerp4', 'domain_object'), 'gel_runtime')
        self.assertEqual(duty_family('c_Instance117', 'domain_object'), 'generated_instance_scaffold')
        self.assertEqual(duty_family('c_AsyncReceiveAllOp', 'domain_object'), 'async_io_runtime')
        self.assertEqual(duty_family('c_IOnSendComplete', 'domain_object'), 'async_io_runtime')
        self.assertEqual(duty_family('c_ClearConsoleCommand', 'domain_object'), 'debug_console')
        self.assertEqual(duty_family('c_Enumerator24', 'collection_iterator'), 'collection_iterator')
        self.assertEqual(duty_family('c_SceneFactory', 'factory'), 'factory')
        self.assertEqual(duty_family('c_ActionAfterPlay', 'domain_object'), 'unresolved')

    def test_owner_trace_accepts_only_unique_upstream_subsystem(self):
        reverse={
            'A': {'B'},
            'B': {'C'},
            'C': {'MATCH'},
        }
        labels={'A':'game_domain_other','B':'game_domain_other','C':'game_domain_other','MATCH':'match_engine'}
        out=trace_owner_candidate('A', reverse, labels, {'A','B','C'}, max_depth=4)
        self.assertEqual(out['candidate'], 'match_engine')
        self.assertEqual(out['confidence'], 'transitive_unique')
        self.assertEqual(out['min_depth'], 3)
        self.assertEqual(out['anchor_counts'], {'match_engine': 1})

    def test_owner_trace_marks_mixed_upstream_subsystems_ambiguous(self):
        reverse={'A': {'B','UI'}, 'B': {'MATCH'}}
        labels={'A':'game_domain_other','B':'game_domain_other','UI':'screen_surface','MATCH':'match_engine'}
        out=trace_owner_candidate('A', reverse, labels, {'A','B'}, max_depth=4)
        self.assertEqual(out['candidate'], 'ambiguous')
        self.assertEqual(out['confidence'], 'mixed')
        self.assertEqual(out['anchor_counts'], {'match_engine': 1, 'screen_surface': 1})

    def test_owner_trace_is_depth_bounded_and_cycle_safe(self):
        reverse={'A': {'B'}, 'B': {'A','C'}, 'C': {'D'}, 'D': {'MATCH'}}
        labels={k:'game_domain_other' for k in ('A','B','C','D')}
        labels['MATCH']='match_engine'
        out=trace_owner_candidate('A', reverse, labels, {'A','B','C','D'}, max_depth=3)
        self.assertEqual(out['candidate'], 'ambiguous')
        self.assertEqual(out['confidence'], 'none')
        self.assertEqual(out['anchor_counts'], {})

if __name__ == '__main__': unittest.main()
