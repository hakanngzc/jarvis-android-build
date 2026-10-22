#!/usr/bin/env python3
import hashlib,json,re,tempfile,zipfile
from pathlib import Path
from dex_model import Dex,app_classes
PKG='Lcom/newstargames/newstarsoccer/'; SCREEN_ROOT=PKG+'c_GScreen;'
def simple(desc): return desc.rsplit('/',1)[-1].removesuffix(';')
def derives(desc,target,by_desc):
    seen=set()
    while desc in by_desc and desc not in seen:
        if desc==target:return True
        seen.add(desc);desc=by_desc[desc]['super']
    return desc==target
def is_screen(row,by_desc):
    n=simple(row['descriptor']);return derives(row['descriptor'],SCREEN_ROOT,by_desc) or n=='c_TScreen' or n.startswith('c_TScreen_') or n.startswith('c_AScreen_')
RULES=[
('android_resources',re.compile(r'^R(?:\$|$)')),
('platform_lifecycle',re.compile(r'^(?:MonkeyGame|AndroidGame|BB(?:Android|Monkey)?Game|BBGameDelegate|c_GameDelegate|c_App|gxtk|GameView|ActivityDelegate|bb_app)')),
('persistence_bootstrap',re.compile(r'(?:GameEngine|Save|Load|State|Prefs|Preference|Serialize|Storage)',re.I)),
('match_engine',re.compile(r'(?:Match|Football|Ball|Pitch|Stadium|Goal|Keeper|Crowd|Replay|Chance|Kick|Shot|Training|Practice|Minigame)',re.I)),
('competition_world',re.compile(r'(?:Competition|Fixture|League|Club|Nation|Country|Promotion|Relegat|Cup|Tournament|Season|Table|Continent)',re.I)),
('career_player',re.compile(r'(?:Player|Career|Contract|Relationship|Skill|Rating|Agent|Sponsor|Boot|Lifestyle|Award|Achievement|Transfer|Retirement|Dilemma)',re.I)),
('cloud_social_commerce',re.compile(r'(?:Cloud|Social|IAP|Purchase|Store|Shop|Product|Ad|Advert|Reward|Currency|Facebook|Twitter|GooglePlay|Analytics|Flurry|Fuse|Ogury|Network)',re.I)),
('data_config',re.compile(r'(?:Data|Tweak|Config|Catalogue|Catalog|Locale|Language|Date|Parse|Json|CSV|Database|Version)',re.I)),
('media_assets',re.compile(r'(?:Audio|Sound|Music|Image|Atlas|Sprite|Spine|Particle|Font|Graphic|Texture|Render|Shader|Anim)',re.I)),
('ui_framework',re.compile(r'(?:Panel|Button|Label|Widget|Gadget|Menu|Dialog|Message|WebPage|Hud|UI|ScreenTemplate)',re.I)),
('input_controls',re.compile(r'(?:Input|Touch|Gesture|Key|Mouse|Joy|Control)',re.I)),
('debug_dev',re.compile(r'(?:Debug|Hack|Test|Dev|Trace|Profiler)',re.I)),
('utility_core',re.compile(r'(?:Stack|List|Map|Set|Array|Pool|Random|Math|String|Builder|Comparator|Iterator|Queue|Rect|Vector|Point|Matrix|Color|Timer|Util)',re.I)),]
def classify(name):
    for cat,rx in RULES:
        if rx.search(name):return cat
    if name.startswith('bb_') or name.startswith('BB'):return 'monkey_framework'
    if name.startswith('c_'):return 'game_domain_other'
    if name.startswith(('Firebase','Fyber','GameHelper','Native','Skn3','Notify','IActivity')):return 'third_party_platform_bridges'
    return 'platform_bridge_other'
def build(apk):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td);dexes=[]
        with zipfile.ZipFile(apk) as z:
            for n in sorted(x for x in z.namelist() if re.fullmatch(r'classes\d*\.dex',Path(x).name)):
                p=td/Path(n).name;p.write_bytes(z.read(n));dexes.append((p.name,Dex(p)))
        rows=app_classes(dexes);by_desc={r['descriptor']:r for r in rows};screens=[r for r in rows if is_screen(r,by_desc)];nons=[r for r in rows if not is_screen(r,by_desc)]
        classmap={simple(r['descriptor']):classify(simple(r['descriptor'])) for r in nons};owners={};fields={}
        for r in rows:
            if r['static_fields']:
                n=simple(r['descriptor']);owners[n]=len(r['static_fields']);fields[n]=[{'name':f['name'],'type':f['type']} for f in r['static_fields']]
        counts={}
        for v in classmap.values():counts[v]=counts.get(v,0)+1
        return {'apk_sha256':hashlib.sha256(Path(apk).read_bytes()).hexdigest(),'app_classes':len(rows),'screen_classes':len(screens),'non_screen_classes':len(nons),'subsystem_counts':dict(sorted(counts.items())),'classmap_sha256':hashlib.sha256(json.dumps(dict(sorted(classmap.items())),separators=(',',':'),sort_keys=True).encode()).hexdigest(),'owners':len(owners),'static_fields':sum(owners.values()),'owner_counts_sha256':hashlib.sha256(json.dumps(dict(sorted(owners.items())),separators=(',',':'),sort_keys=True).encode()).hexdigest(),'strings':sorted(set(s for _,d in dexes for s in d.strings)),'classes':sorted(simple(r['descriptor']) for r in rows)}
