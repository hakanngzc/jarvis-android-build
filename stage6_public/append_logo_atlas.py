#!/usr/bin/env python3
import hashlib
import json
import struct
import sys
from pathlib import Path

from inspect_key_tail import headers, parse_record_end


def _pad4(buf,absolute_start):
    while (absolute_start+len(buf))%4:
        buf.append(0)


def _pascal(buf,s,absolute_start):
    raw=s.encode('ascii')
    if not raw or len(raw)>255:
        raise ValueError(f'invalid Pascal string length for {s!r}')
    buf.append(len(raw)); buf.extend(raw); _pad4(buf,absolute_start)


def find_alias_offset(data):
    hs=headers(data)
    if not hs:
        raise ValueError('no atlas headers found')
    prefix=struct.unpack_from('<I',data,0)[0]
    if prefix!=len(hs):
        raise ValueError(f'atlas count/header mismatch: prefix={prefix}, headers={len(hs)}')
    h=hs[-1]; pos=h['records_offset']
    for idx in range(h['count']):
        end,meta=parse_record_end(data,pos)
        if end is None or end<=pos or end>len(data):
            raise ValueError(f"cannot parse final atlas record {idx} at {pos}: {meta}")
        pos=end
    return pos,hs


def append_atlas(data,atlas_name,width,height,records):
    data=bytes(data)
    if not (1<=width<=8192 and 1<=height<=8192):
        raise ValueError('atlas dimensions out of range')
    if not records:
        raise ValueError('at least one image record is required')
    insert,hs=find_alias_offset(data)
    if any(h['name']==atlas_name for h in hs):
        raise ValueError(f'atlas already exists: {atlas_name}')
    old_count=struct.unpack_from('<I',data,0)[0]
    alias_before=data[insert:]
    chunk=bytearray()
    _pascal(chunk,atlas_name,insert)
    chunk.extend(struct.pack('<III',width,height,len(records)))
    record_names=[]
    for rec in records:
        name=rec['name']; rd=list(rec['render_data'])
        if len(rd)!=8:
            raise ValueError(f'{name}: render_data must contain 8 floats')
        dims=[int(rec[k]) for k in ('original_width','original_height','trimmed_width','trimmed_height')]
        if any(v<0 or v>65535 for v in dims):
            raise ValueError(f'{name}: dimensions out of ushort range')
        # Use the stock normal-image record form: flags=0, Pascal refname,
        # four unsigned-short dimensions, eight render floats.
        chunk.extend(struct.pack('<I',0))
        _pascal(chunk,name,insert)
        chunk.extend(struct.pack('<4H8f',*dims,*[float(x) for x in rd]))
        record_names.append(name)
    out=bytearray(data[:insert])
    out.extend(chunk)
    out.extend(alias_before)
    struct.pack_into('<I',out,0,old_count+1)
    alias_after=bytes(out[insert+len(chunk):])
    before_sha=hashlib.sha256(alias_before).hexdigest()
    after_sha=hashlib.sha256(alias_after).hexdigest()
    if alias_before!=alias_after or before_sha!=after_sha:
        raise AssertionError('alias suffix changed during append')
    if bytes(out[4:insert])!=data[4:insert]:
        raise AssertionError('existing atlas bytes changed during append')
    meta={
        'old_atlas_count':old_count,'new_atlas_count':old_count+1,
        'insert_offset':insert,'inserted_size':len(chunk),'new_atlas_name':atlas_name,
        'atlas_width':width,'atlas_height':height,'record_names':record_names,
        'alias_suffix_size':len(alias_before),
        'alias_suffix_sha256_before':before_sha,'alias_suffix_sha256_after':after_sha,
        'source_prefix_sha256':hashlib.sha256(data[4:insert]).hexdigest(),
        'patched_prefix_sha256':hashlib.sha256(bytes(out[4:insert])).hexdigest(),
    }
    return bytes(out),meta


def main():
    if len(sys.argv)!=5:
        raise SystemExit(f'usage: {sys.argv[0]} IN.key OUT.key SPEC.json REPORT.json')
    src,outp,specp,reportp=map(Path,sys.argv[1:])
    spec=json.loads(specp.read_text(encoding='utf-8'))
    out,meta=append_atlas(src.read_bytes(),spec['atlas_name'],int(spec['width']),int(spec['height']),spec['records'])
    outp.write_bytes(out); reportp.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print(f"APPEND_ATLAS=PASS old={meta['old_atlas_count']} new={meta['new_atlas_count']} name={meta['new_atlas_name']} records={len(meta['record_names'])} insert={meta['insert_offset']}")

if __name__=='__main__': main()
