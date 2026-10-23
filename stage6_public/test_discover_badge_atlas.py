#!/usr/bin/env python3
import struct, tempfile, unittest, zipfile
from pathlib import Path

import discover_badge_atlas as d


def add_record(b,name,flags,w,h,boxes):
    while (len(b)+4)%4: b += b'\0'
    b += struct.pack('<I',flags)
    raw=name.encode(); b += bytes([len(raw)])+raw
    while len(b)%4: b += b'\0'
    if flags==8:
        # Stock flag8: logical width/height + variable mesh vertices (x,y,u,v),
        # followed by one 4-byte terminal field before the next record.
        b += struct.pack('<2H',w,h)
        for box in boxes:
            x0,y0,x1,y1=box
            u0,v0,u1,v1=x0/1024,y0/1024,x1/1024,y1/1024
            b += struct.pack('<16f',0,0,u0,v0, 1,0,u1,v0, 0,1,u0,v1, 1,1,u1,v1)
        b += struct.pack('<I',0)
    else:
        x0,y0,x1,y1=boxes[0]
        bw,bh=x1-x0,y1-y0
        b += struct.pack('<4H',bw,bh,bw,bh)
        b += struct.pack('<8f',0,0,x0/1024,y0/1024,0,0,x1/1024,y1/1024)
    return b


def packed_metadata(flag8_mesh=False):
    b=bytearray(); ah=b'UIAtlas2'
    b += bytes([len(ah)])+ah
    while len(b)%4: b += b'\0'
    b += struct.pack('<III',1024,1024,2)
    if flag8_mesh:
        # First quad is deliberately only 12x4. The second expands the real
        # sprite region to 64x64; a four-vertex-only parser must fail this test.
        add_record(b,'MapShieldDesign7',8,210,285,[(100,200,112,204),(100,200,164,264)])
    else:
        add_record(b,'MapShieldDesign7',0,64,64,[(100,200,164,264)])
    add_record(b,'MapShieldWhite',0,32,32,[(300,300,332,332)])
    return bytes(b)


class DiscoveryTests(unittest.TestCase):
    def make_apk(self,td,record):
        apk=td/'base.apk'
        shield='''Macro:(M_TestShield)\n Image:(MapShieldWhite)\n Image:(MapShieldDesign7)\n SetColour:(Badge1Col1)\n Tweak:(BadgeStyle1)\nEndM\n'''
        clubs='id\tshortname\thomestyle\thomekitshirtcol1\thomekitshirtcol2\tnationid\tleagueid\tcontinentalcompid\tbteamof\n3141\tBesiktas\t7\t1\t2\t193\t7270\t432\t0\n'
        with zipfile.ZipFile(apk,'w') as z:
            z.writestr('assets/monkey/NewGUI/Common/ShieldAnims.uih',shield)
            z.writestr('assets/monkey/UI/packed-images.dat',record)
            z.writestr('assets/monkey/MyData/v2025/Clubs.txt',clubs)
        return apk

    def assert_contract(self,r):
        self.assertEqual(r['shield_ui']['files'][0]['path'],'assets/monkey/NewGUI/Common/ShieldAnims.uih')
        self.assertIn('BadgeStyle1',r['shield_ui']['tokens'])
        rec=next(x for x in r['atlas_symbols'] if x['name']=='MapShieldDesign7')
        self.assertEqual(rec['atlas'],'UIAtlas2')
        self.assertEqual(rec['box'],[100,200,164,264])
        self.assertEqual(rec['key_path'],'assets/monkey/UI/packed-images.dat')
        self.assertEqual(r['clubs']['fields'][2],'homestyle')
        return rec

    def test_metadata_is_discovered_by_signature_not_extension(self):
        with tempfile.TemporaryDirectory() as raw:
            td=Path(raw); apk=self.make_apk(td,packed_metadata(False))
            self.assert_contract(d.discover(apk,td/'out'))

    def test_flag8_full_mesh_uv_bounds_are_resolved(self):
        with tempfile.TemporaryDirectory() as raw:
            td=Path(raw); apk=self.make_apk(td,packed_metadata(True))
            rec=self.assert_contract(d.discover(apk,td/'out'))
            self.assertEqual(rec['flags'],8)
            self.assertEqual(rec['record_layout'],'flag8_mesh')
            self.assertEqual(rec['mesh_vertex_count'],8)


if __name__=='__main__': unittest.main()
