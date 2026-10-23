#!/usr/bin/env python3
import csv
import hashlib
import io
import json
import re
import struct
import sys
import zipfile
from pathlib import Path


def align(v,n=4): return (v+n-1)&~(n-1)


def scan_atlas_headers(data):
    out=[]
    for m in re.finditer(rb'UIAtlas\d+(?:_VOL)?',data):
        s=m.start(); raw=m.group(); name=raw.decode('ascii')
        if s<1 or data[s-1] != len(raw):
            continue
        p=align(s+len(raw),4)
        if p+12>len(data):
            continue
        w,h,count=struct.unpack_from('<III',data,p)
        if 0<w<=8192 and 0<h<=8192 and count<20000:
            out.append({'offset':s-1,'name':name,'width':w,'height':h,'count':count})
    return sorted(out,key=lambda x:x['offset'])


def nearest_header(headers,off):
    prev=None
    for h in headers:
        if h['offset']<off: prev=h
        else: break
    return prev


def find_pascal_positions(data,name):
    raw=name.encode('utf-8'); pat=bytes([len(raw)])+raw
    out=[]; start=0
    while True:
        i=data.find(pat,start)
        if i<0: break
        if i%4==0: out.append(i)
        start=i+1
    return out


def read_normal_record(data,name,key_path):
    headers=scan_atlas_headers(data)
    for i in find_pascal_positions(data,name):
        if i<4: continue
        flags=struct.unpack_from('<I',data,i-4)[0]
        if flags & (2|4|8): continue
        p=align(i+1+len(name.encode('utf-8')),4)
        if p+40>len(data): continue
        ow,oh,tw,th=struct.unpack_from('<4H',data,p); p+=8
        rd=struct.unpack_from('<8f',data,p)
        atlas=nearest_header(headers,i)
        if not atlas: continue
        u0,u1=sorted((rd[2],rd[6])); v0,v1=sorted((rd[3],rd[7]))
        box=[round(u0*atlas['width']),round(v0*atlas['height']),round(u1*atlas['width']),round(v1*atlas['height'])]
        if box[2] <= box[0] or box[3] <= box[1]: continue
        return {
            'name':name,'key_path':key_path,'flags':flags,'offset':i,
            'atlas':atlas['name'],'atlas_width':atlas['width'],'atlas_height':atlas['height'],
            'original_width':ow,'original_height':oh,'trimmed_width':tw,'trimmed_height':th,
            'box':box,
        }
    return None


def ui_hits(path,text):
    pats=('MapShield','BadgeStyle','Badge1Col','Badge2Col','ShieldAnim','Shield')
    lines=[]
    for n,line in enumerate(text.splitlines(),1):
        if any(p.lower() in line.lower() for p in pats):
            lines.append({'line':n,'text':line.rstrip()})
    return lines


def is_metadata_candidate(name,data):
    low=name.lower()
    if low.endswith('.key'):
        return True
    return b'MapShield' in data or (b'UIAtlas' in data and not low.endswith(('.png','.jpg','.jpeg','.webp')))


def occurrence_diagnostics(data):
    headers=scan_atlas_headers(data); out=[]
    for m in re.finditer(rb'MapShield[A-Za-z0-9_]{0,64}',data):
        off=m.start(); name=m.group().decode('ascii','replace'); h=nearest_header(headers,off)
        lo=max(0,off-20); hi=min(len(data),off+len(m.group())+64)
        out.append({
            'name':name,'ascii_offset':off,'ascii_offset_mod4':off%4,
            'byte_before':data[off-1] if off else None,
            'expected_pascal_length':len(m.group()),
            'preceding_u32_le':struct.unpack_from('<I',data,off-4)[0] if off>=4 else None,
            'window_start':lo,'window_hex':data[lo:hi].hex(),
            'nearest_atlas':h['name'] if h else None,
            'nearest_atlas_offset':h['offset'] if h else None,
            'distance_from_atlas_header':off-h['offset'] if h else None,
        })
    return out


def discover(apk_path,out_dir):
    apk_path=Path(apk_path); out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    report={
        'apk_sha256':hashlib.sha256(apk_path.read_bytes()).hexdigest(),
        'shield_ui':{'files':[],'tokens':[]},
        'metadata_files':[],
        'atlas_symbols':[],
        'atlas_files':[],
        'clubs':{},
    }
    tokens=set(); symbol_names=set(); metadata_blobs=[]
    with zipfile.ZipFile(apk_path) as z:
        names=z.namelist()
        for info in z.infolist():
            name=info.filename; low=name.lower()
            if low.endswith(('.uih','.uis')):
                try: text=z.read(name).decode('utf-8-sig')
                except Exception: continue
                hits=ui_hits(name,text)
                if hits:
                    report['shield_ui']['files'].append({
                        'path':name,
                        'sha256':hashlib.sha256(text.encode('utf-8')).hexdigest(),
                        'hits':hits,
                    })
                    tokens.update(re.findall(r'\b(?:MapShield[A-Za-z0-9_]*|Badge[A-Za-z0-9_]*|[A-Za-z0-9_]*Shield[A-Za-z0-9_]*)\b',text))
                    symbol_names.update(re.findall(r'\bMapShield[A-Za-z0-9_]*\b',text))
                    if name.endswith('ShieldAnims.uih'):
                        (out_dir/'ShieldAnims.uih.txt').write_text(text,encoding='utf-8')
            if re.search(r'(?:^|/)UIAtlas\d+(?:_VOL)?\.png$',name):
                report['atlas_files'].append(name)
            if info.is_dir() or info.file_size>32*1024*1024 or low.endswith(('.png','.jpg','.jpeg','.webp','.dex')):
                continue
            try: data=z.read(name)
            except Exception: continue
            if is_metadata_candidate(name,data):
                headers=scan_atlas_headers(data); diags=occurrence_diagnostics(data)
                metadata_blobs.append((name,data))
                report['metadata_files'].append({
                    'path':name,'size':len(data),
                    'mapshield_ascii_occurrences':data.count(b'MapShield'),
                    'atlas_headers':[h['name'] for h in headers],
                    'atlas_header_count':len(headers),
                    'mapshield_record_diagnostics':diags,
                })
        clubs=[n for n in names if n.endswith('/v2025/Clubs.txt')]
        if len(clubs)==1:
            raw=z.read(clubs[0]).decode('utf-8-sig')
            rows=list(csv.DictReader(io.StringIO(raw),delimiter='\t'))
            fields=list(rows[0].keys()) if rows else []
            idx={str(r.get('id','')).strip():r for r in rows if str(r.get('id','')).strip().isdigit()}
            sample_ids=['3141','3157','3163','3190','3232']
            report['clubs']={
                'path':clubs[0],
                'fields':fields,
                'numeric_row_count':len(idx),
                'badge_candidate_fields':[f for f in fields if any(x in f.lower() for x in ('style','colour','color','kit','badge','shield'))],
                'samples':{i:idx[i] for i in sample_ids if i in idx},
            }
    for meta_path,data in metadata_blobs:
        for m in re.finditer(rb'MapShield[A-Za-z0-9_]{0,64}',data):
            try: symbol_names.add(m.group().decode('ascii'))
            except Exception: pass
    records=[]
    for name in sorted(symbol_names):
        for meta_path,data in metadata_blobs:
            rec=read_normal_record(data,name,meta_path)
            if rec:
                records.append(rec); break
    report['shield_ui']['tokens']=sorted(tokens)
    report['shield_ui']['files']=sorted(report['shield_ui']['files'],key=lambda x:x['path'])
    report['metadata_files']=sorted(report['metadata_files'],key=lambda x:x['path'])
    report['atlas_symbols']=sorted(records,key=lambda x:(x['atlas'],x['name']))
    report['atlas_files']=sorted(report['atlas_files'])
    out=(out_dir/'stage6-badge-atlas-discovery.json')
    out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"shield_ui_files={len(report['shield_ui']['files'])} tokens={len(tokens)} metadata_files={len(report['metadata_files'])} atlas_symbols={len(records)} atlas_files={len(report['atlas_files'])} club_rows={report.get('clubs',{}).get('numeric_row_count',0)}")
    print(f"report={out}")
    return report


def main():
    if len(sys.argv)!=3:
        raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT_DIR')
    discover(sys.argv[1],sys.argv[2])


if __name__=='__main__': main()
