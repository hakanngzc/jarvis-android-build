#!/usr/bin/env python3
import argparse, collections, hashlib, json, re, struct, tempfile, zipfile
from pathlib import Path

APP='Lcom/newstargames/newstarsoccer/'
ROOT=APP+'c_GScreen;'
LEGACY_RE=re.compile(r'^Lcom/newstargames/newstarsoccer/(c_(?:TScreen|AScreen)_[^;]+|c_TScreen);$')
RULES = [
    ('android_resources', re.compile(r'^R(?:\$|$)')),
    ('platform_lifecycle', re.compile(r'^(?:MonkeyGame|AndroidGame|BB(?:Android|Monkey)?Game|BBGameDelegate|c_GameDelegate|c_App|gxtk|GameView|ActivityDelegate|bb_app)')),
    ('persistence_bootstrap', re.compile(r'(?:GameEngine|Save|Load|State|Prefs|Preference|Serialize|Storage)', re.I)),
    ('match_engine', re.compile(r'(?:Match|Football|Ball|Pitch|Stadium|Goal|Keeper|Crowd|Replay|Chance|Kick|Shot|Training|Practice|Minigame)', re.I)),
    ('competition_world', re.compile(r'(?:Competition|Fixture|League|Club|Nation|Country|Promotion|Relegat|Cup|Tournament|Season|Table|Continent)', re.I)),
    ('career_player', re.compile(r'(?:Player|Career|Contract|Relationship|Skill|Rating|Agent|Sponsor|Boot|Lifestyle|Award|Achievement|Transfer|Retirement|Dilemma)', re.I)),
    ('cloud_social_commerce', re.compile(r'(?:Cloud|Social|IAP|Purchase|Store|Shop|Product|Ad|Advert|Reward|Currency|Facebook|Twitter|GooglePlay|Analytics|Flurry|Fuse|Ogury|Network)', re.I)),
    ('data_config', re.compile(r'(?:Data|Tweak|Config|Catalogue|Catalog|Locale|Language|Date|Parse|Json|CSV|Database|Version)', re.I)),
    ('media_assets', re.compile(r'(?:Audio|Sound|Music|Image|Atlas|Sprite|Spine|Particle|Font|Graphic|Texture|Render|Shader|Anim)', re.I)),
    ('ui_framework', re.compile(r'(?:Panel|Button|Label|Widget|Gadget|Menu|Dialog|Message|WebPage|Hud|UI|ScreenTemplate)', re.I)),
    ('input_controls', re.compile(r'(?:Input|Touch|Gesture|Key|Mouse|Joy|Control)', re.I)),
    ('debug_dev', re.compile(r'(?:Debug|Hack|Test|Dev|Trace|Profiler)', re.I)),
    ('utility_core', re.compile(r'(?:Stack|List|Map|Set|Array|Pool|Random|Math|String|Builder|Comparator|Iterator|Queue|Rect|Vector|Point|Matrix|Color|Timer|Util)', re.I)),
]

def simple(desc): return desc.rsplit('/',1)[-1].rstrip(';')
def legacy_screen(desc): return bool(LEGACY_RE.match(desc))
def derives(desc, root, supers):
    seen=set()
    while desc and desc not in seen:
        if desc==root:return True
        seen.add(desc); desc=supers.get(desc)
    return False

def canonical_screen(desc, supers):
    n=simple(desc)
    return derives(desc,ROOT,supers) or n=='c_TScreen' or n.startswith('c_TScreen_') or n.startswith('c_AScreen_')

def classify_name(desc):
    n=simple(desc)
    for label,rx in RULES:
        if rx.search(n): return label
    if n.startswith('bb_') or n.startswith('BB'): return 'monkey_framework'
    if n.startswith('c_'): return 'game_domain_other'
    if n.startswith(('Firebase','Fyber','GameHelper','Native','Skn3','Notify','IActivity')): return 'third_party_platform_bridges'
    return 'platform_bridge_other'

class Dex:
    def __init__(self,path):
        self.path=str(path); self.b=Path(path).read_bytes(); b=self.b
        if not b.startswith(b'dex\n'): raise ValueError(path)
        self.string_n,self.string_off=struct.unpack_from('<II',b,0x38)
        self.type_n,self.type_off=struct.unpack_from('<II',b,0x40)
        self.proto_n,self.proto_off=struct.unpack_from('<II',b,0x48)
        self.field_n,self.field_off=struct.unpack_from('<II',b,0x50)
        self.method_n,self.method_off=struct.unpack_from('<II',b,0x58)
        self.class_n,self.class_off=struct.unpack_from('<II',b,0x60)
        self.strings=[self._string(struct.unpack_from('<I',b,self.string_off+4*i)[0]) for i in range(self.string_n)]
        self.types=[self.strings[struct.unpack_from('<I',b,self.type_off+4*i)[0]] for i in range(self.type_n)]
        self.protos=[]
        for i in range(self.proto_n):
            _,ret,params=struct.unpack_from('<III',b,self.proto_off+12*i); ps=[]
            if params:
                n=struct.unpack_from('<I',b,params)[0]; ps=[self.types[struct.unpack_from('<H',b,params+4+2*j)[0]] for j in range(n)]
            self.protos.append((self.types[ret],ps))
        self.fields=[]
        for i in range(self.field_n):
            ci,ti,ni=struct.unpack_from('<HHI',b,self.field_off+8*i); self.fields.append((self.types[ci],self.strings[ni],self.types[ti]))
        self.methods=[]
        for i in range(self.method_n):
            ci,pi,ni=struct.unpack_from('<HHI',b,self.method_off+8*i); self.methods.append((self.types[ci],self.strings[ni],self.protos[pi]))
        self.class_defs=[]
        for i in range(self.class_n):
            ci,access,superi,interfaces,source,ann,data,_=struct.unpack_from('<8I',b,self.class_off+32*i)
            self.class_defs.append({'descriptor':self.types[ci],'access':access,'super':None if superi==0xffffffff else self.types[superi],'interfaces_off':interfaces,'data_off':data})
    def uleb(self,o):
        r=0;s=0
        while True:
            x=self.b[o];o+=1;r|=(x&0x7f)<<s
            if x<128:return r,o
            s+=7
    def _string(self,o):
        _,o=self.uleb(o); e=self.b.index(0,o); return self.b[o:e].decode('utf-8','replace')
    def class_data(self,cd):
        o=cd['data_off']; out={'fields':[],'methods':[]}
        if not o:return out
        sf,o=self.uleb(o); inf,o=self.uleb(o); dm,o=self.uleb(o); vm,o=self.uleb(o)
        for count in (sf,inf):
            idx=0
            for _ in range(count):
                diff,o=self.uleb(o); idx+=diff; access,o=self.uleb(o); cls,name,typ=self.fields[idx]
                out['fields'].append({'index':idx,'name':name,'type':typ,'access':access})
        for count in (dm,vm):
            idx=0
            for _ in range(count):
                diff,o=self.uleb(o); idx+=diff; access,o=self.uleb(o); code,o=self.uleb(o); cls,name,proto=self.methods[idx]
                out['methods'].append({'index':idx,'name':name,'return':proto[0],'params':proto[1],'code_off':code})
        return out
    def method_refs(self,code_off):
        if not code_off:return set(),set(),set()
        b=self.b; struct.unpack_from('<4H',b,code_off); _,sz=struct.unpack_from('<2I',b,code_off+8); p=code_off+16
        u=list(struct.unpack_from('<%dH'%sz,b,p)); clsrefs=set(); methodrefs=set(); fieldrefs=set(); i=0
        widths=[1]*256
        for op in [0x02,0x05,0x08]: widths[op]=2
        for op in [0x03,0x06,0x09]: widths[op]=3
        for op in range(0x13,0x17): widths[op]=2
        widths[0x17]=3; widths[0x18]=5; widths[0x19]=2; widths[0x1a]=2; widths[0x1b]=3; widths[0x1c]=2
        for op in [0x1f,0x20,0x22,0x23]: widths[op]=2
        for op in [0x24,0x25,0x26,0x2a,0x2b,0x2c]: widths[op]=3
        widths[0x29]=2
        for op in range(0x2d,0x3e): widths[op]=2
        for op in range(0x44,0x6e): widths[op]=2
        for op in range(0x6e,0x73): widths[op]=3
        for op in range(0x74,0x79): widths[op]=3
        for op in range(0x90,0xb0): widths[op]=2
        for op in range(0xd0,0xe3): widths[op]=2
        for op in [0xfa,0xfb,0xfc,0xfd]: widths[op]=3
        widths[0xfe]=2; widths[0xff]=2
        while i < len(u):
            op=u[i]&0xff; w=widths[op]
            if op==0 and (u[i]>>8) in (1,2,3):
                ident=u[i]>>8
                if ident==1: w=4+u[i+1]*2
                elif ident==2: w=2+u[i+1]*4
                else:
                    elem=u[i+1]; n=u[i+2]|(u[i+3]<<16); w=4+(elem*n+1)//2
            try:
                if op in range(0x6e,0x73) or op in range(0x74,0x79):
                    idx=u[i+1]; cls,mn,_=self.methods[idx]; methodrefs.add((cls,mn)); clsrefs.add(cls)
                elif op in range(0x52,0x6e):
                    idx=u[i+1]; cls,fn,ft=self.fields[idx]; fieldrefs.add((cls,fn,ft)); clsrefs.update((cls,ft))
                elif op in (0x22,0x1c,0x1f,0x20,0x23): clsrefs.add(self.types[u[i+1]])
            except Exception: pass
            i += max(w,1)
        return clsrefs,methodrefs,fieldrefs

def analyze_dexes(dex_paths, source_sha=None):
    dexes=[(Path(p).name,Dex(p)) for p in dex_paths]
    rows=[]; supers={}
    for dn,d in dexes:
        for cd in d.class_defs:
            if not cd['descriptor'].startswith(APP):continue
            row={'dex':dn,**cd,**d.class_data(cd)}; rows.append(row); supers[cd['descriptor']]=cd['super']
    screens={r['descriptor'] for r in rows if canonical_screen(r['descriptor'],supers)}
    legacy={r['descriptor'] for r in rows if legacy_screen(r['descriptor'])}
    nonscreen=[r for r in rows if r['descriptor'] not in screens]
    catch=[r for r in nonscreen if classify_name(r['descriptor'])=='game_domain_other']
    class_label={r['descriptor']:classify_name(r['descriptor']) for r in nonscreen}
    dex_by={dn:d for dn,d in dexes}
    reverse=collections.defaultdict(set); details=[]; temp={}
    for r in catch:
        refs=set(); methods=set(); fields=set()
        if r['super']: refs.add(r['super'])
        for f in r['fields']: refs.add(f['type'])
        for m in r['methods']:
            refs.add(m['return']); refs.update(m['params'])
            cr,mr,fr=dex_by[r['dex']].method_refs(m['code_off']); refs.update(cr); methods.update(mr); fields.update(fr)
        refs={x for x in refs if x.startswith(APP) and x!=r['descriptor']}
        for x in refs: reverse[x].add(r['descriptor'])
        temp[r['descriptor']]={'row':r,'refs':refs,'methodrefs':methods,'fieldrefs':fields}
    for desc,t in temp.items():
        r=t['row']; peer_counts=collections.Counter(class_label[x] for x in t['refs'] if x in class_label and class_label[x]!='game_domain_other')
        ranked=peer_counts.most_common(); inferred='ambiguous'; confidence='none'
        if ranked:
            topn,topc=ranked[0]; second=ranked[1][1] if len(ranked)>1 else 0
            if topc>=3 and topc>=max(2,second*2): inferred=topn; confidence='high'
            elif topc>=2 and topc>second: inferred=topn; confidence='medium'
        details.append({
            'class':simple(desc),'descriptor':desc,'dex':r['dex'],'super':r['super'],
            'declared_field_count':len(r['fields']),'declared_method_count':len(r['methods']),
            'app_reference_count':len(t['refs']),'app_references':sorted(simple(x) for x in t['refs']),
            'incoming_catchall_reference_count':len(reverse.get(desc,set())),
            'incoming_catchall_references':sorted(simple(x) for x in reverse.get(desc,set())),
            'anchored_subsystem_counts':dict(sorted(peer_counts.items())),
            'semantic_candidate':inferred,'semantic_confidence':confidence,
        })
    sem=collections.Counter(x['semantic_candidate'] for x in details)
    conf=collections.Counter(x['semantic_confidence'] for x in details)
    return {
      'schema':1,'source_sha256':source_sha,
      'class_counts':{'app_classes':len(rows),'canonical_screen_surfaces':len(screens),'legacy_screen_surfaces':len(legacy),'non_screen_classes':len(nonscreen),'game_domain_other':len(catch)},
      'screen_reconciliation':{
        'canonical_rule':'c_GScreen descendants OR c_TScreen/c_TScreen_* OR c_AScreen_*',
        'legacy_rule':'name-only c_TScreen/c_TScreen_* or c_AScreen_*',
        'canonical_count':len(screens),'legacy_count':len(legacy),
        'canonical_only':[simple(x) for x in sorted(screens-legacy)],
        'legacy_only':[simple(x) for x in sorted(legacy-screens)],
      },
      'catchall_relationship_summary':{
        'classes_mapped':len(details),'semantic_candidates':dict(sorted(sem.items())),'confidence_counts':dict(sorted(conf.items())),
        'rule':'candidate labels are inferred only from exact direct references to already-name-classified non-catchall peers; relationship facts remain authoritative and candidate labels are not treated as proven duties.'
      },
      'game_domain_other_relationships':sorted(details,key=lambda x:x['class'])
    }

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--xapk'); ap.add_argument('--base-apk'); ap.add_argument('--out',required=True); a=ap.parse_args()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        if a.xapk:
            xsha=hashlib.sha256(Path(a.xapk).read_bytes()).hexdigest()
            with zipfile.ZipFile(a.xapk) as z: base=td/'base.apk'; base.write_bytes(z.read('com.newstargames.newstarsoccer.apk'))
        else:
            base=Path(a.base_apk); xsha=None
        dex=[]
        with zipfile.ZipFile(base) as z:
            for n in sorted(x for x in z.namelist() if re.fullmatch(r'classes\d*\.dex',x)):
                p=td/n; p.write_bytes(z.read(n)); dex.append(p)
        out=analyze_dexes(dex,xsha); Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'counts':out['class_counts'],'screen':out['screen_reconciliation'],'catchall':out['catchall_relationship_summary']},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
