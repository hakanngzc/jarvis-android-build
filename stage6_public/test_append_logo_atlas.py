import struct
import unittest

from append_logo_atlas import append_atlas


def align(v,n=4): return (v+n-1)&~(n-1)


def pascal_at(buf,s):
    raw=s.encode('ascii'); buf.append(len(raw)); buf.extend(raw)
    while len(buf)%4: buf.append(0)


def normal_record(buf,name,ow=16,oh=16,tw=16,th=16,rd=(0,0,0,0,16,16,1,1)):
    buf.extend(struct.pack('<I',0)); pascal_at(buf,name)
    buf.extend(struct.pack('<4H8f',ow,oh,tw,th,*rd))


def synthetic_key():
    b=bytearray(struct.pack('<I',1))
    pascal_at(b,'UIAtlas1'); b.extend(struct.pack('<III',64,64,1))
    normal_record(b,'Existing')
    alias=b'\x03Old\x08Existing\x00'
    b.extend(alias)
    return bytes(b),alias


class AppendAtlasTests(unittest.TestCase):
    def test_append_preserves_existing_bytes_and_alias_suffix(self):
        src,alias=synthetic_key()
        records=[
            {'name':'REBORNClub3141','original_width':32,'original_height':32,'trimmed_width':32,'trimmed_height':32,
             'render_data':[0.0,0.0,0.0,0.0,32.0,32.0,0.5,1.0]},
            {'name':'REBORNClub3157','original_width':32,'original_height':32,'trimmed_width':32,'trimmed_height':32,
             'render_data':[0.0,0.0,0.5,0.0,32.0,32.0,1.0,1.0]},
        ]
        out,meta=append_atlas(src,'UIAtlas2',64,32,records)
        self.assertEqual(struct.unpack_from('<I',out,0)[0],2)
        self.assertEqual(meta['old_atlas_count'],1)
        self.assertEqual(meta['new_atlas_count'],2)
        self.assertEqual(meta['new_atlas_name'],'UIAtlas2')
        self.assertEqual(meta['record_names'],['REBORNClub3141','REBORNClub3157'])
        self.assertEqual(out[4:meta['insert_offset']],src[4:meta['insert_offset']])
        self.assertEqual(out[-len(alias):],alias)
        self.assertEqual(meta['alias_suffix_sha256_before'],meta['alias_suffix_sha256_after'])
        self.assertGreater(len(out),len(src))


if __name__=='__main__': unittest.main()
