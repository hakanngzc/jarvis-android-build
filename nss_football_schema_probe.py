#!/usr/bin/env python3
# Provenance: NSS 4.31 v2025 schema probe, 2026-10-29.
import csv, hashlib, io, json, re, sys, zipfile
from pathlib import Path

BASE_APK='com.newstargames.newstarsoccer.apk'
VERSION='v2025'
ROOT=f'assets/monkey/MyData/{VERSION}/'
RELATIONS={
 ('Clubs.txt','nationid'):('Nations.txt','id',True),
 ('Clubs.txt','leagueid'):('Competitions.txt','id',True),
 ('Clubs.txt','continentalcompid'):('Competitions.txt','id',True),
 ('Clubs.txt','bteamof'):('Clubs.txt','id',True),
 ('Nations.txt','continent'):('Continents.txt','id',True),
 ('PromotionPlaces.txt','parentid'):('Competitions.txt','id',False),
 ('PromotionPlaces.txt','promotiontoid'):('Competitions.txt','id',False),
}

def meta(v):
    v=(v or '').strip()
    return not v or v.startswith('//') or v.startswith('#') or v.startswith(';')

def typ(vals):
    vals=[str(v).strip() for v in vals if str(v).strip()]
    if not vals:return 'empty'
    if all(re.fullmatch(r'[+-]?\d+',v) for v in vals):return 'integer'
    try:
        [float(v) for v in vals]
        return 'number'
    except ValueError:return 'string'

def parse(name, raw):
    text=raw.decode('utf-8-sig')
    r=csv.DictReader(io.StringIO(text),delimiter='\t')
    cols=list(r.fieldnames or [])
    rows=list(r)
    data=[x for x in rows if not meta(x.get(cols[0],''))]
    metas=[x for x in rows if meta(x.get(cols[0],''))]
    fields={}
    for i,c in enumerate(cols):
        vals=[x.get(c,'') or '' for x in data]
        t=typ(vals)
        f={'position':i,'value_type':t,'empty_count':sum(not str(v).strip() for v in vals),'zero_count':sum(str(v).strip() in {'0','0.0'} for v in vals),'unique_count':len(set(map(str,vals)))}
        nums=[]
        if t=='integer': nums=[int(v) for v in vals if str(v).strip()]
        elif t=='number': nums=[float(v) for v in vals if str(v).strip()]
        if nums:f.update(min=min(nums),max=max(nums))
        fields[c]=f
    return {'name':name,'columns':cols,'fields':fields,'raw_row_count':len(rows),'data_row_count':len(data),'metadata_row_count':len(metas),'metadata_positions':[i for i,x in enumerate(rows) if meta(x.get(cols[0],''))],'asset_sha256':hashlib.sha256(raw).hexdigest(),'_data':data}

def main():
    src=Path(sys.argv[1]); out=Path(sys.argv[2]); md=Path(sys.argv[3])
    xb=src.read_bytes(); xsha=hashlib.sha256(xb).hexdigest()
    with zipfile.ZipFile(io.BytesIO(xb)) as z: bb=z.read(BASE_APK)
    bsha=hashlib.sha256(bb).hexdigest(); tables={}
    with zipfile.ZipFile(io.BytesIO(bb)) as z:
        names=sorted(n for n in z.namelist() if n.startswith(ROOT) and n.endswith('.txt') and '/' not in n[len(ROOT):])
        for n in names:
            name=n[len(ROOT):]; tables[name]=parse(name,z.read(n))
    checks=[]; broken_total=0
    for (st,sc),(dt,dc,zero) in RELATIONS.items():
        if st not in tables or dt not in tables or sc not in tables[st]['columns'] or dc not in tables[dt]['columns']:continue
        valid={str(x.get(dc,'')).strip() for x in tables[dt]['_data']}; broken=[]; zeros=0; checked=0
        for row in tables[st]['_data']:
            v=str(row.get(sc,'')).strip()
            if v in {'','0'} and zero:
                zeros += int(v=='0'); continue
            checked += 1
            if v not in valid: broken.append(v)
        broken_total += len(broken)
        checks.append({'table':st,'column':sc,'references':f'{dt}.{dc}','allow_zero_sentinel':zero,'checked_count':checked,'zero_sentinel_count':zeros,'broken_count':len(broken),'broken_values':sorted(set(broken))[:50]})
    clean={k:{kk:vv for kk,vv in v.items() if kk!='_data'} for k,v in tables.items()}
    report={'schema':1,'generated_by':'nss_football_schema_probe.py','input':{'xapk_sha256':xsha,'base_apk_sha256':bsha,'database_version':VERSION},'summary':{'table_count':len(clean),'tables':sorted(clean),'total_raw_rows':sum(v['raw_row_count'] for v in clean.values()),'total_data_rows':sum(v['data_row_count'] for v in clean.values()),'total_metadata_rows':sum(v['metadata_row_count'] for v in clean.values()),'broken_reference_count':broken_total},'tables':clean,'relations':{'broken_reference_count':broken_total,'checks':checks}}
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    lines=['# NSS 4.31 v2025 football database schema probe','',f"Tables: {len(clean)}",f"Broken refs: {broken_total}",'']
    for name in sorted(clean):
        t=clean[name]; lines += [f'## {name}',f"Rows: {t['data_row_count']} data / {t['metadata_row_count']} metadata",f"Header: `{' | '.join(t['columns'])}`",'']
        for c in t['columns']:
            f=t['fields'][c]; lines.append(f"- `{c}` — {f['value_type']} — empty {f['empty_count']} — zero {f['zero_count']} — unique {f['unique_count']}")
        lines.append('')
    md.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('TABLES='+','.join(sorted(clean)))
    for name in sorted(clean): print(name+': '+' | '.join(clean[name]['columns']))
    print(f'BROKEN_REFS={broken_total}')
    if broken_total: raise SystemExit(2)

if __name__=='__main__': main()
