#!/usr/bin/env python3
import json, math, re, struct, sys, zipfile
from pathlib import Path


def align(v,n=4): return (v+n-1)&~(n-1)


def headers(data):
    out=[]
    for m in re.finditer(rb'UIAtlas\d+(?:_VOL)?',data):
        s=m.start(); raw=m.group()
        if s<1 or data[s-1] != len(raw): continue
        p=align(s+len(raw),4)
        if p+12>len(data): continue
        w,h,count=struct.unpack_from('<III',data,p)
        if 0<w<=8192 and 0<h<=8192 and count<20000:
            out.append({'name':raw.decode(),'offset':s-1,'width':w,'height':h,'count':count,'records_offset':p+12})
    return sorted(out,key=lambda x:x['offset'])


def variable_triangles_end(data,p):
    groups=0
    while p+4<=len(data):
        first=struct.unpack_from('<f',data,p)[0]
        if first == -1.0:
            return p+4,groups
        if p+48>len(data): return None,None
        vals=struct.unpack_from('<12f',data,p)
        if not all(math.isfinite(x) for x in vals): return None,None
        p+=48; groups+=1
        if groups>10000: return None,None
    return None,None


def parse_record_end(data,pos):
    if pos+5>len(data): return None,{'reason':'eof-before-record'}
    flags=struct.unpack_from('<I',data,pos)[0]
    ns=pos+4; n=data[ns]
    if not (1<=n<=255) or ns+1+n>len(data):
        return None,{'reason':'bad-name-length','flags':flags,'name_length':n}
    raw=data[ns+1:ns+1+n]
    try: name=raw.decode('ascii')
    except Exception: return None,{'reason':'non-ascii-name','flags':flags,'name_hex':raw.hex()}
    p=align(ns+1+n,4)
    base={'flags':flags,'name':name,'body_offset':p}
    if flags & 1:
        return None,{**base,'reason':'bit1-extra-metadata-needs-layout-proof'}
    if flags & 2:
        q=p+12
        end,groups=variable_triangles_end(data,q)
        return end,{**base,'layout':'sliced','triangle_groups':groups}
    if flags & 8:
        q=p+4
        end,groups=variable_triangles_end(data,q)
        return end,{**base,'layout':'stripped','triangle_groups':groups}
    if flags & 4:
        dims=list(struct.unpack_from('<4H',data,p)) if p+8<=len(data) else None
        return p+8,{**base,'layout':'packed','dimensions':dims}
    if flags==0:
        if p+40>len(data): return None,{**base,'reason':'eof-normal-body'}
        dims=list(struct.unpack_from('<4H',data,p)); rd=list(struct.unpack_from('<8f',data,p+8))
        return p+40,{**base,'layout':'normal','dimensions':dims,'render_data':rd}
    return None,{**base,'reason':'unsupported-flags'}


def main():
    if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.json')
    apk=Path(sys.argv[1]); out=Path(sys.argv[2])
    with zipfile.ZipFile(apk) as z:
        data=z.read('assets/monkey/NewGUI/Atlases/Key.key')
    hs=headers(data)
    if not hs: raise SystemExit('no atlas headers')
    h=hs[-1]; pos=h['records_offset']; recs=[]; parsed=True; stop={}
    for idx in range(h['count']):
        end,meta=parse_record_end(data,pos)
        item={'index':idx,'start':pos,**meta}
        if end is None or end<=pos or end>len(data):
            item['end']=end; recs.append(item); parsed=False; stop=item; break
        item['end']=end; recs.append(item); pos=end
    alias={}
    if parsed:
        alias['offset']=pos
        if pos<len(data):
            n=data[pos]
            alias['first_length']=n
            alias['first_bytes_hex']=data[pos:min(len(data),pos+96)].hex()
            if n and pos+1+n<=len(data):
                alias['first_string']=data[pos+1:pos+1+n].decode('utf-8','replace')
    counts={}
    for r in recs:
        k=r.get('layout','STOP'); counts[k]=counts.get(k,0)+1
    normal_samples=[r for r in recs if r.get('layout')=='normal'][:5]
    report={'key_size':len(data),'atlas_count_prefix':struct.unpack_from('<I',data,0)[0],
            'header_count_found':len(hs),'last_atlas':h,'parsed_record_count':len(recs) if parsed else max(0,len(recs)-1),
            'layout_counts':counts,'normal_samples':normal_samples,'records':recs,'parsed_all_last_atlas_records':parsed,
            'stop_record':stop,'alias_probe':alias}
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+'\n')
    print(f"KEY_TAIL_SCAN last={h['name']} count={h['count']} parsed_records={report['parsed_record_count']} all={parsed} layouts={counts} alias_offset={alias.get('offset')} normal_samples={len(normal_samples)}")

if __name__=='__main__': main()
