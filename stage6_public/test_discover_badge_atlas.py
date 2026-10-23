#!/usr/bin/env python3
import struct, tempfile, unittest, zipfile
from pathlib import Path

import discover_badge_atlas as d


def add_record(b,name,flags,w,h,triangles):
    while (len(b)+4)%4: b += b'\0'
    b += struct.pack('<I',flags)
    raw=name.encode(); b += bytes([len(raw)])+raw
    while len(b)%4: b += b'\0'
    if flags==8:
        b += struct.pack('<2H',w,h)
        for tri in triangles:
            vals=[]
            for x,y,u,v in tri:
                vals += [x,y,u,v]
            if len(vals)!=12: raise AssertionError('triangle must have 3 xyuv vertices')
            b += struct.pack('<12f',*vals)
        b += struct.pack('<f',-1.0)
    else:
        x0,y0,x1,y1=triangles[0]
        bw,bh=x1-x0,y1-y0
        b += struct.pack('<4H',bw,bh,bw,bh)
        b += struct.pack('<8f',0,0,x0/1024,y0/1024,0,0,x1/1024,y1/1024)
    return b


def packed_metadata(stripped=False):
    b=bytearray(); ah=b'UIAtlas2'
    b += bytes([len(ah)])+ah
    while len(b)%4: b += b'\0'
    b += struct.pack('<III',1024,1024,2)
    if stripped:
        # Two separate triangles. The first covers only a tiny 12x4 UV area;
        # the second reaches the intended 64x64 global extent. The parser must
        # preserve triangle fragments rather than pretend this is one crop.
        t1=[(0.0,0.0,100/1024,200/1024),(1.0,0.0,112/1024,200/1024),(0.0,1.0,100/1024,204/1024)]
        t2=[(0.0,0.0,100/1024,200/1024),(1.0,0.0,164/1024,200/1024),(0.0,1.0,100/1024,264/1024)]
        add_record(b,'MapShieldDesign7',8,210,285,[t1,t2])
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

    def assert_base_contract(self,r):
        self.assertEqual(r['shield_ui']['files'][0]['path'],'assets/monkey/NewGUI/Common/ShieldAnims.uih')
        self.assertIn('BadgeStyle1',r['shield_ui']['tokens'])
        rec=next(x for x in r['atlas_symbols'] if x['name']=='MapShieldDesign7')
        self.assertEqual(rec['atlas'],'UIAtlas2')
        self.assertEqual(rec['key_path'],'assets/monkey/UI/packed-images.dat')
        self.assertEqual(r['clubs']['fields'][2],'homestyle')
        return rec

    def test_metadata_is_discovered_by_signature_not_extension(self):
        with tempfile.TemporaryDirectory() as raw:
            td=Path(raw); apk=self.make_apk(td,packed_metadata(False))
            rec=self.assert_base_contract(d.discover(apk,td/'out'))
            self.assertEqual(rec['box'],[100,200,164,264])
            self.assertEqual(rec['record_layout'],'normal')

    def test_flag8_is_stripped_triangles_terminated_by_minus_one(self):
        with tempfile.TemporaryDirectory() as raw:
            td=Path(raw); apk=self.make_apk(td,packed_metadata(True))
            rec=self.assert_base_contract(d.discover(apk,td/'out'))
            self.assertEqual(rec['flags'],8)
            self.assertEqual(rec['record_layout'],'stripped_triangles')
            self.assertEqual(rec['triangle_count'],2)
            self.assertEqual(rec['render_float_count'],24)
            self.assertTrue(rec['sentinel_found'])
            self.assertFalse(rec['contiguous_atlas_box'])
            self.assertEqual(rec['fragment_uv_boxes'][0],[100,200,112,204])
            self.assertEqual(rec['fragment_uv_boxes'][1],[100,200,164,264])
            self.assertNotIn('box',rec)


if __name__=='__main__': unittest.main()
