#!/usr/bin/env python3
import argparse, collections, json, re, sys, tempfile, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from residual_static.nss_residual_static_analysis import APP, Dex, canonical_screen, classify_name, simple

COLLECTION_ITERATOR_RE=re.compile(r'^c_(?:Enumerator|IDepEnumerator|ValueEnumerator|NodeEnumerator)\d*$')
COLLECTION_NODE_RE=re.compile(r'^c_Node\d*$')
COLLECTION_IFACE_RE=re.compile(r'^c_ICollection\d*$')

def structural_role(name):
    if COLLECTION_ITERATOR_RE.match(name): return 'collection_iterator'
    if COLLECTION_NODE_RE.match(name): return 'collection_node'
    if COLLECTION_IFACE_RE.match(name): return 'collection_interface'
    if name.endswith('Factory'): return 'factory'
    if name.endswith('Exception') or name.endswith('Error'): return 'exception_or_error'
    return 'domain_object'

def choose_candidate(counts):
    ranked=sorted(counts.items(),key=lambda x:(-x[1],x[0]))
    if not ranked:return 'ambiguous','none'
    topn,topc=ranked[0]; second=ranked[1][1] if len(ranked)>1 else 0
    if topc>=5 and topc>=second*2:return topn,'high'
    if topc>=3 and topc>second:return topn,'medium'
    return 'ambiguous','none'

def trace_owner_candidate(start, reverse, labels, catch, max_depth=4):
    """Trace exact incoming-reference ownership through catch-all classes.

    This is intentionally separate from semantic duty inference.  We emit an
    owner candidate only when every anchored upstream caller reached within the
    bounded reverse-reference walk belongs to the same known subsystem.
    Cycles are visited once and mixed subsystem evidence remains ambiguous.
    """
    seen={start}; frontier=[start]; anchors=collections.Counter(); min_depth={}
    for depth in range(1,max_depth+1):
        nxt=[]
        for current in frontier:
            for owner in sorted(reverse.get(current,set())):
                label=labels.get(owner,'external')
                if owner in catch or label=='game_domain_other':
                    if owner not in seen:
                        seen.add(owner); nxt.append(owner)
                    continue
                if label=='external':
                    continue
                anchors[label]+=1
                min_depth[label]=min(min_depth.get(label,depth),depth)
        frontier=nxt
        if not frontier:
            break
    ordered=dict(sorted(anchors.items()))
    if not anchors:
        return {'candidate':'ambiguous','confidence':'none','min_depth':None,'anchor_counts':ordered}
    if len(anchors)!=1:
        return {'candidate':'ambiguous','confidence':'mixed','min_depth':min(min_depth.values()),'anchor_counts':ordered}
    candidate=next(iter(anchors))
    depth=min_depth[candidate]
    return {
        'candidate':candidate,
        'confidence':'direct_unique' if depth==1 else 'transitive_unique',
        'min_depth':depth,
        'anchor_counts':ordered,
    }

def class_refs(d,row):
    refs=set(); method_targets=set(); field_targets=set()
    if row['super']: refs.add(row['super'])
    for f in row['fields']: refs.add(f['type'])
    for m in row['methods']:
        refs.add(m['return']); refs.update(m['params'])
        if m['code_off']:
            cr,mr,fr=d.method_refs(m['code_off']); refs.update(cr); method_targets.update(mr); field_targets.update(fr)
    refs={x for x in refs if x.startswith(APP) and x!=row['descriptor']}
    return refs,method_targets,field_targets

def analyze(base_apk):
    with tempfile.TemporaryDirectory(prefix='nss-catchall-refine-') as td:
        td=Path(td); dexes=[]; rows=[]; supers={}
        with zipfile.ZipFile(base_apk) as z:
            for name in sorted(n for n in z.namelist() if re.fullmatch(r'classes\d*\.dex',n)):
                p=td/name; p.write_bytes(z.read(name)); dexes.append((name,Dex(p)))
        dby={n:d for n,d in dexes}
        for dn,d in dexes:
            for cd in d.class_defs:
                if not cd['descriptor'].startswith(APP):continue
                row={'dex':dn,**cd,**d.class_data(cd)}; rows.append(row); supers[row['descriptor']]=row['super']
        screens={r['descriptor'] for r in rows if canonical_screen(r['descriptor'],supers)}
        labels={r['descriptor']:('screen_surface' if r['descriptor'] in screens else classify_name(r['descriptor'])) for r in rows}
        catch={r['descriptor'] for r in rows if r['descriptor'] not in screens and labels[r['descriptor']]=='game_domain_other'}
        outgoing={}; method_targets={}; field_targets={}; reverse=collections.defaultdict(set)
        by={r['descriptor']:r for r in rows}
        for r in rows:
            refs,mr,fr=class_refs(dby[r['dex']],r); outgoing[r['descriptor']]=refs; method_targets[r['descriptor']]=mr; field_targets[r['descriptor']]=fr
            for target in refs: reverse[target].add(r['descriptor'])
        # Exact catchall connected components, useful even when no semantic subsystem is safe.
        adj={c:set() for c in catch}
        for c in catch:
            for x in outgoing[c]:
                if x in catch: adj[c].add(x); adj[x].add(c)
            for x in reverse[c]:
                if x in catch: adj[c].add(x); adj[x].add(c)
        component={}; component_sizes={}; cid=0
        for c in sorted(catch):
            if c in component:continue
            cid+=1; stack=[c]; component[c]=cid; members=[]
            while stack:
                u=stack.pop(); members.append(u)
                for v in adj[u]:
                    if v not in component:component[v]=cid; stack.append(v)
            component_sizes[cid]=len(members)
        details=[]
        for c in sorted(catch):
            r=by[c]
            inowners=sorted(reverse[c])
            outrefs=sorted(outgoing[c])
            incoming_counts=collections.Counter(labels[x] for x in inowners if labels.get(x)!='game_domain_other')
            outgoing_counts=collections.Counter(labels[x] for x in outrefs if labels.get(x)!='game_domain_other')
            combined=incoming_counts+outgoing_counts
            candidate,confidence=choose_candidate(dict(combined))
            owner_trace=trace_owner_candidate(c,reverse,labels,catch,max_depth=4)
            details.append({
              'class':simple(c),'descriptor':c,'dex':r['dex'],'super':r['super'],
              'structural_role':structural_role(simple(c)),
              'component_id':component[c],'component_size':component_sizes[component[c]],
              'declared_fields':[{'name':f['name'],'type':f['type']} for f in r['fields']],
              'declared_methods':[m['name'] for m in r['methods']],
              'incoming_owner_count':len(inowners),
              'incoming_owners':[{'class':simple(x),'label':labels.get(x,'external')} for x in inowners],
              'outgoing_reference_count':len(outrefs),
              'outgoing_references':[{'class':simple(x),'label':labels.get(x,'external')} for x in outrefs],
              'incoming_anchor_counts':dict(sorted(incoming_counts.items())),
              'outgoing_anchor_counts':dict(sorted(outgoing_counts.items())),
              'combined_anchor_counts':dict(sorted(combined.items())),
              'semantic_candidate':candidate,'semantic_confidence':confidence,
              'owner_candidate':owner_trace['candidate'],
              'owner_confidence':owner_trace['confidence'],
              'owner_min_depth':owner_trace['min_depth'],
              'owner_anchor_counts':owner_trace['anchor_counts'],
              'method_target_count':len(method_targets[c]),'field_target_count':len(field_targets[c]),
            })
        sem=collections.Counter(x['semantic_candidate'] for x in details)
        conf=collections.Counter(x['semantic_confidence'] for x in details)
        owner=collections.Counter(x['owner_candidate'] for x in details)
        owner_conf=collections.Counter(x['owner_confidence'] for x in details)
        roles=collections.Counter(x['structural_role'] for x in details)
        return {
          'schema':2,
          'classes_mapped':len(details),
          'component_count':len(component_sizes),
          'component_sizes':dict(sorted(component_sizes.items())),
          'semantic_candidates':dict(sorted(sem.items())),
          'confidence_counts':dict(sorted(conf.items())),
          'owner_candidates':dict(sorted(owner.items())),
          'owner_confidence_counts':dict(sorted(owner_conf.items())),
          'structural_roles':dict(sorted(roles.items())),
          'classes':details,
        }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('base_apk',type=Path); ap.add_argument('--out',required=True,type=Path); a=ap.parse_args()
    d=analyze(a.base_apk); a.out.parent.mkdir(parents=True,exist_ok=True); a.out.write_text(json.dumps(d,indent=2),encoding='utf-8')
    print(json.dumps({k:d[k] for k in ('classes_mapped','component_count','semantic_candidates','confidence_counts','owner_candidates','owner_confidence_counts','structural_roles')},indent=2))
if __name__=='__main__': main()
