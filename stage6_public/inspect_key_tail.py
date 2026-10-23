#!/usr/bin/env python3
import json, re, struct, sys, zipfile
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


def main():
    if len(sys.argv)!=3: raise SystemExit(f'usage: {sys.argv[0]} BASE.apk OUT.json')
    apk=Path(sys.argv[1]); out=Path(sys.argv[2])
    with zipfile.ZipFile(apk) as z:
        data=z.read('assets/monkey/NewGUI/Atlases/Key.key')
    hs=headers(data)
    if not hs: raise SystemExit('no atlas headers')
    h=hs[-1]; pos=h['records_offset']; recs=[]; parsed=True
    for idx in range(h['count']):
        if pos+5>len(data): parsed=False; break
        flags=struct.unpack_from('<I',data,pos)[0]
        ns=pos+4; n=data[ns]; raw=data[ns+1:ns+1+n]
        try: name=raw.decode('ascii')
        except Exception: name=raw.hex()
        p=align(ns+1+n,4)
        item={'index':idx,'start':pos,'flags':flags,'name':name}
        if flags==0:
            end=p+40
        else:
            item['unsupported_for_tail_parser']=True
            recs.append(item); parsed=False; break
        item['end']=end; recs.append(item); pos=end
    alias={}
    if parsed:
        alias['offset']=pos
        if pos<len(data):
            n=data[pos]
            alias['first_length']=n
            alias['first_bytes_hex']=data[pos:min(len(data),pos+64)].hex()
            if n and pos+1+n<=len(data):
                alias['first_string']=data[pos+1:pos+1+n].decode('utf-8','replace')
    report={'key_size':len(data),'atlas_count_prefix':struct.unpack_from('<I',data,0)[0],
            'header_count_found':len(hs),'last_atlas':h,'records':recs,'all_last_records_normal':parsed,'alias_probe':alias}
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(report,indent=2)+'\n')
    print(f"KEY_TAIL_SCAN last={h['name']} count={h['count']} parsed={parsed} alias_offset={alias.get('offset')} key_size={len(data)}")

if __name__=='__main__': main()
