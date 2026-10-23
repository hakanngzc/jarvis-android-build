#!/usr/bin/env python3
import csv, hashlib, io, json, math, re, struct, sys, zipfile
from pathlib import Path


def align(v,n=4): return (v+n-1)&~(n-1)


def scan_atlas_headers(data):
    out=[]
    for m in re.finditer(rb'UIAtlas\d+(?:_VOL)?',data):
        s=m.start(); raw=m.group(); name=raw.decode('ascii')
        if s<1 or data[s-1]!=len(raw): continue
        p=align(s+len(raw),4)
        if p+12>len(data): continue
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
    raw=name.encode(); pat=bytes([len(raw)])+raw; out=[]; start=0
    while True:
        i=data.find(pat,start)
        if i<0: return out
        if i%4==0: out.append(i)
        start=i+1


def parse_normal(data,p,atlas):
    if p+40>len(data): return None
    ow,oh,tw,th=struct.unpack_from('<4H',data,p); p+=8
    rd=struct.unpack_from('<8f',data,p)
    u0,u1=sorted((rd[2],rd[6])); v0,v1=sorted((rd[3],rd[7]))
    if not all(math.isfinite(x) for x in (u0,u1,v0,v1)): return None
    box=[round(u0*atlas['width']),round(v0*atlas['height']),round(u1*atlas['width']),round(v1*atlas['height'])]
    if box[2]<=box[0] or box[3]<=box[1]: return None
    return {
        'record_layout':'normal','original_width':ow,'original_height':oh,
        'trimmed_width':tw,'trimmed_height':th,'box':box,
    }


def parse_stripped(data,p,atlas):
    # c_AtlasManager.m_ReadStrippedImage on stock 4.31 reads original width/
    # height, then repeated groups of 12 floats. The first float of the next
    # group is tested against -1.0; that sentinel terminates the record.
    if p+8>len(data): return None
    ow,oh=struct.unpack_from('<2H',data,p); q=p+4
    triangles=[]; render_float_count=0; sentinel_offset=None
    while q+4<=len(data):
        first=struct.unpack_from('<f',data,q)[0]
        if first==-1.0:
            sentinel_offset=q; q+=4; break
        if q+48>len(data): return None
        vals=struct.unpack_from('<12f',data,q)
        if not all(math.isfinite(v) for v in vals): return None
        verts=[vals[0:4],vals[4:8],vals[8:12]]
        us=[v[2] for v in verts]; vs=[v[3] for v in verts]
        if min(us)<-0.001 or max(us)>1.001 or min(vs)<-0.001 or max(vs)>1.001:
            return None
        box=[round(min(us)*atlas['width']),round(min(vs)*atlas['height']),round(max(us)*atlas['width']),round(max(vs)*atlas['height'])]
        triangles.append({'uv_box':box})
        render_float_count+=12; q+=48
        if len(triangles)>10000: return None
    if sentinel_offset is None or not triangles: return None
    all_boxes=[t['uv_box'] for t in triangles]
    global_extent=[min(b[0] for b in all_boxes),min(b[1] for b in all_boxes),max(b[2] for b in all_boxes),max(b[3] for b in all_boxes)]
    return {
        'record_layout':'stripped_triangles','original_width':ow,'original_height':oh,
        'triangle_count':len(triangles),'render_float_count':render_float_count,
        'sentinel_found':True,'sentinel_offset':sentinel_offset,'record_end_offset':q,
        'contiguous_atlas_box':False,'fragment_uv_boxes':all_boxes,
        'global_uv_extent_diagnostic_only':global_extent,
    }


def read_image_record(data,name,key_path):
    headers=scan_atlas_headers(data)
    for i in find_pascal_positions(data,name):
        if i<4: continue
        flags=struct.unpack_from('<I',data,i-4)[0]
        if flags not in (0,8): continue
        atlas=nearest_header(headers,i)
        if not atlas: continue
        p=align(i+1+len(name.encode()),4)
        body=parse_stripped(data,p,atlas) if flags==8 else parse_normal(data,p,atlas)
        if not body: continue
        return {
            'name':name,'key_path':key_path,'flags':flags,'offset':i,
            'atlas':atlas['name'],'atlas_width':atlas['width'],'atlas_height':atlas['height'],
            **body,
        }
    return None


def ui_hits(text):
    pats=('MapShield','BadgeStyle','Badge1Col','Badge2Col','ShieldAnim','Shield')
    return [{'line':n,'text':line.rstrip()} for n,line in enumerate(text.splitlines(),1) if any(p.lower() in line.lower() for p in pats)]


def metadata_candidate(name,data):
    low=name.lower()
    return low.endswith('.key') or b'MapShield' in data or (b'UIAtlas' in data and not low.endswith(('.png','.jpg','.jpeg','.webp')))


def occurrence_diagnostics(data):
    headers=scan_atlas_headers(data); out=[]
    for m in re.finditer(rb'MapShield[A-Za-z0-9_]{0,64}',data):
        off=m.start(); pascal=off-1; h=nearest_header(headers,off)
        out.append({
            'name':m.group().decode('ascii','replace'),'ascii_offset':off,
            'record_flags_u32':struct.unpack_from('<I',data,pascal-4)[0] if pascal>=4 else None,
            'nearest_atlas':h['name'] if h else None,
        })
    return out


def discover(apk_path,out_dir):
    apk_path=Path(apk_path); out_dir=Path(out_dir); out_dir.mkdir(parents=True,exist_ok=True)
    report={'apk_sha256':hashlib.sha256(apk_path.read_bytes()).hexdigest(),'shield_ui':{'files':[],'tokens':[]},'metadata_files':[],'atlas_symbols':[],'atlas_files':[],'clubs':{}}
    tokens=set(); symbol_names=set(); metadata=[]
    with zipfile.ZipFile(apk_path) as z:
        names=z.namelist()
        for info in z.infolist():
            name=info.filename; low=name.lower()
            if low.endswith(('.uih','.uis')):
                try: text=z.read(name).decode('utf-8-sig')
                except Exception: text=None
                if text is not None:
                    hits=ui_hits(text)
                    if hits:
                        report['shield_ui']['files'].append({'path':name,'sha256':hashlib.sha256(text.encode()).hexdigest(),'hits':hits})
                        tokens.update(re.findall(r'\b(?:MapShield[A-Za-z0-9_]*|Badge[A-Za-z0-9_]*|[A-Za-z0-9_]*Shield[A-Za-z0-9_]*)\b',text))
                        symbol_names.update(re.findall(r'\bMapShield[A-Za-z0-9_]*\b',text))
                        if name.endswith('ShieldAnims.uih'): (out_dir/'ShieldAnims.uih.txt').write_text(text,encoding='utf-8')
            if re.search(r'(?:^|/)UIAtlas\d+(?:_VOL)?\.png$',name): report['atlas_files'].append(name)
            if info.is_dir() or info.file_size>32*1024*1024 or low.endswith(('.png','.jpg','.jpeg','.webp','.dex')): continue
            try: data=z.read(name)
            except Exception: continue
            if metadata_candidate(name,data):
                headers=scan_atlas_headers(data); metadata.append((name,data))
                report['metadata_files'].append({'path':name,'size':len(data),'mapshield_ascii_occurrences':data.count(b'MapShield'),'atlas_header_count':len(headers),'atlas_headers':[h['name'] for h in headers],'mapshield_record_diagnostics':occurrence_diagnostics(data)})
        clubs=[n for n in names if n.endswith('/v2025/Clubs.txt')]
        if len(clubs)==1:
            raw=z.read(clubs[0]).decode('utf-8-sig'); rows=list(csv.DictReader(io.StringIO(raw),delimiter='\t')); fields=list(rows[0]) if rows else []
            idx={str(r.get('id','')).strip():r for r in rows if str(r.get('id','')).strip().isdigit()}
            samples=['3141','3157','3163','3190','3232']
            report['clubs']={'path':clubs[0],'fields':fields,'numeric_row_count':len(idx),'badge_candidate_fields':[f for f in fields if any(x in f.lower() for x in ('style','colour','color','kit','badge','shield'))],'samples':{i:idx[i] for i in samples if i in idx}}
    for _,data in metadata:
        for m in re.finditer(rb'MapShield[A-Za-z0-9_]{0,64}',data):
            try: symbol_names.add(m.group().decode('ascii'))
            except Exception: pass
    for symbol in sorted(symbol_names):
        for path,data in metadata:
            rec=read_image_record(data,symbol,path)
            if rec: report['atlas_symbols'].append(rec); break
    report['shield_ui']['tokens']=sorted(tokens); report['shield_ui']['files'].sort(key=lambda x:x['path']); report['metadata_files'].sort(key=lambda x:x['path']); report['atlas_symbols'].sort(key=lambda x:(x['atlas'],x['name'])); report['atlas_files'].sort()
    out=out_dir/'stage6-badge-atlas-discovery.json'; out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"shield_ui_files={len(report['shield_ui']['files'])} tokens={len(tokens)} metadata_files={len(report['metadata_files'])} atlas_symbols={len(report['atlas_symbols'])} atlas_files={len(report['atlas_files'])} club_rows={report.get('clubs',{}).get('numeric_row_count',0)}")
    print(f'report={out}'); return report


def main():
    if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT_DIR')
    discover(sys.argv[1],sys.argv[2])

if __name__=='__main__': main()
