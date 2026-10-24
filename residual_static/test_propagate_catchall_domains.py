import unittest

from propagate_catchall_domains import propagate_details


def row(name, candidate='ambiguous', confidence='none', anchors=None, incoming=None, outgoing=None, role='domain_object'):
    return {
        'class': name,
        'structural_role': role,
        'semantic_candidate': candidate,
        'semantic_confidence': confidence,
        'combined_anchor_counts': anchors or {},
        'incoming_owners': [{'class': x, 'label': 'game_domain_other'} for x in (incoming or [])],
        'outgoing_references': [{'class': x, 'label': 'game_domain_other'} for x in (outgoing or [])],
    }


class CatchallPropagationTest(unittest.TestCase):
    def test_single_neighbor_never_resolves_class(self):
        details = [
            row('Seed', 'career_player', 'high', {'career_player': 5}),
            row('Unknown', incoming=['Seed']),
        ]
        out = propagate_details(details)
        got = {x['class']: x for x in out['classes']}
        self.assertEqual(got['Unknown']['owner_domain_status'], 'unresolved')

    def test_three_independent_resolved_neighbors_can_resolve(self):
        details = [
            row('A', 'career_player', 'high', {'career_player': 5}),
            row('B', 'career_player', 'medium', {'career_player': 3}),
            row('C', 'career_player', 'high', {'career_player': 6}),
            row('Unknown', anchors={'career_player': 1}, incoming=['A', 'B'], outgoing=['C']),
        ]
        out = propagate_details(details)
        got = {x['class']: x for x in out['classes']}
        self.assertEqual(got['Unknown']['resolved_owner_domain'], 'career_player')
        self.assertEqual(got['Unknown']['owner_domain_evidence']['kind'], 'graph_propagation')

    def test_conflicting_neighbors_fail_closed(self):
        details = [
            row('A', 'career_player', 'high', {'career_player': 5}),
            row('B', 'match_engine', 'high', {'match_engine': 5}),
            row('C', 'match_engine', 'high', {'match_engine': 6}),
            row('Unknown', incoming=['A', 'B'], outgoing=['C']),
        ]
        out = propagate_details(details)
        got = {x['class']: x for x in out['classes']}
        self.assertEqual(got['Unknown']['owner_domain_status'], 'unresolved')

    def test_structural_helper_is_not_given_gameplay_domain(self):
        out = propagate_details([row('Enumerator7', role='collection_iterator')])
        self.assertEqual(out['classes'][0]['resolved_owner_domain'], 'structural:collection_iterator')


if __name__ == '__main__':
    unittest.main()
