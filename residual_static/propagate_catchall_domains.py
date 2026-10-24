#!/usr/bin/env python3
import argparse
import collections
import json
from pathlib import Path

from refine_catchall_owners import analyze


def propagate_details(details):
    by = {d['class']: d for d in details}
    resolved = {}
    reason = {}

    # Structural framework helpers are already meaningfully resolved without
    # pretending they own a gameplay subsystem.
    for name, d in by.items():
        if d['structural_role'] != 'domain_object':
            resolved[name] = 'structural:' + d['structural_role']
            reason[name] = {'kind': 'structural_role', 'role': d['structural_role']}

    # Direct anchor seeds use the stricter owner/refiner confidence already
    # computed from exact DEX references to non-catchall subsystem classes.
    for name, d in by.items():
        if name in resolved:
            continue
        if d['semantic_candidate'] != 'ambiguous' and d['semantic_confidence'] in ('high', 'medium'):
            resolved[name] = d['semantic_candidate']
            reason[name] = {
                'kind': 'direct_anchor',
                'confidence': d['semantic_confidence'],
                'anchors': d['combined_anchor_counts'],
            }

    rounds = 0
    while True:
        rounds += 1
        pending = []
        for name, d in by.items():
            if name in resolved or d['structural_role'] != 'domain_object':
                continue
            votes = collections.Counter()
            independent = collections.defaultdict(set)

            # Exact non-catchall anchors count double. They are stronger than
            # propagated catchall-neighbor evidence.
            for domain, count in d['combined_anchor_counts'].items():
                if domain != 'game_domain_other':
                    votes[domain] += count * 2
                    independent[domain].add('anchor:' + domain)

            neighbors = set()
            for x in d['incoming_owners'] + d['outgoing_references']:
                peer = x['class']
                if peer != name and peer in by:
                    neighbors.add(peer)
            for peer in neighbors:
                domain = resolved.get(peer)
                if not domain or domain.startswith('structural:'):
                    continue
                votes[domain] += 1
                independent[domain].add('peer:' + peer)

            ranked = votes.most_common()
            if not ranked:
                continue
            top, score = ranked[0]
            second = ranked[1][1] if len(ranked) > 1 else 0
            direct_top = d['combined_anchor_counts'].get(top, 0)
            peer_support = sum(1 for s in independent[top] if s.startswith('peer:'))

            # Fail closed: propagation requires a dominant score plus multiple
            # independent evidence sources. A single named neighbor can never
            # resolve another class by itself.
            enough_sources = peer_support >= 3 or (direct_top >= 2 and peer_support >= 2)
            if score >= 5 and score >= max(2, second * 2) and enough_sources:
                pending.append((name, top, score, second, direct_top, sorted(independent[top])))

        if not pending:
            break
        # Apply only after evaluating the whole round so ordering cannot affect
        # which classes resolve in that round.
        for name, top, score, second, direct_top, sources in pending:
            resolved[name] = top
            reason[name] = {
                'kind': 'graph_propagation',
                'round': rounds,
                'score': score,
                'second_score': second,
                'direct_anchor_count': direct_top,
                'independent_sources': sources,
            }
        if rounds >= 20:
            break

    out = []
    for d in details:
        row = dict(d)
        name = d['class']
        if name in resolved:
            row['resolved_owner_domain'] = resolved[name]
            row['owner_domain_evidence'] = reason[name]
            row['owner_domain_status'] = 'resolved'
        else:
            row['resolved_owner_domain'] = 'ambiguous'
            row['owner_domain_evidence'] = {'kind': 'insufficient_evidence'}
            row['owner_domain_status'] = 'unresolved'
        out.append(row)

    summary = collections.Counter(r['resolved_owner_domain'] for r in out)
    unresolved = sum(r['owner_domain_status'] == 'unresolved' for r in out)
    structural = sum(r['resolved_owner_domain'].startswith('structural:') for r in out)
    semantic = len(out) - unresolved - structural
    return {
        'classes_mapped': len(out),
        'propagation_rounds': rounds,
        'resolved_semantic_domain': semantic,
        'resolved_structural_role': structural,
        'unresolved': unresolved,
        'resolved_owner_domains': dict(sorted(summary.items())),
        'classes': out,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base_apk', type=Path)
    ap.add_argument('--out', required=True, type=Path)
    args = ap.parse_args()
    base = analyze(args.base_apk)
    result = propagate_details(base['classes'])
    result['schema'] = 1
    result['source'] = 'refine_catchall_owners exact DEX relationship graph'
    result['rule'] = (
        'Resolved owner domains require direct exact subsystem anchors or a dominant multi-source graph consensus. '
        'Unresolved classes remain ambiguous; labels are owner-domain evidence, not invented per-class gameplay duties.'
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('classes_mapped','propagation_rounds','resolved_semantic_domain','resolved_structural_role','unresolved','resolved_owner_domains')}, indent=2))


if __name__ == '__main__':
    main()
