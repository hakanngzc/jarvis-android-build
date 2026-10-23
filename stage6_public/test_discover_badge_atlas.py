#!/usr/bin/env python3
import struct, tempfile, unittest, zipfile
from pathlib import Path

import discover_badge_atlas as d


def pascal_record(name, atlas_name='UIAtlas2', w=1024, h=1024, box=(100,200,164,264)):
    # Minimal synthetic packed metadata layout matching the stock normal-record contract.
    b=bytearray()
    ah=atlas_name.encode()
    b += bytes([len(ah)]) + ah
    while len(b)%4: b += b'\0'
    b += struct.pack('<III',w,h,1)
    while len(b)%4: b += b'\0'
    while (len(b)+4)%4: b += b'\0'
    b += struct.pack('<I',0)
    raw=name.encode()
    b += bytes([len(raw)])+raw
    while len(b)%4: b += b'\0'
    bw,bh=box[2]-box[0],box[3]-box[1]
    b += struct.pack('<4H',bw,bh,bw,bh)
    u0,v0,u1,v1=box[0]/w,box[1]/h,box[2]/w,box[3]/h
    b += struct.pack('<8f',0,0,u0,v0,0,0,u1,v1)
    return bytes(b)


class DiscoveryTests(unittest.TestCase):
    def test_ui_and_atlas_contract_is_extracted_without_key_extension_assumption(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td); apk=td/'base.apk'; out=td/'out'
            packed=pascal_record('MapShieldDesign7')
            shield='''Macro:(M_TestShield)\n Image:(MapShieldWhite)\n Image:(MapShieldDesign7)\n SetColour:(Badge1Col1)\n Tweak:(BadgeStyle1)\nEndM\n'''
            clubs='id\tshortname\thomestyle\thomekitshirtcol1\thomekitshirtcol2\tnationid\tleagueid\tcontinentalcompid\tbteamof\n3141\tBesiktas\t7\t1\t2\t193\t7270\t432\t0\n'
            with zipfile.ZipFile(apk,'w') as z:
                z.writestr('assets/monkey/NewGUI/Common/ShieldAnims.uih',shield)
                # Deliberately not .key: discovery must follow the binary signature.
                z.writestr('assets/monkey/UI/packed-images.dat',packed)
                z.writestr('assets/monkey/MyData/v2025/Clubs.txt',clubs)
            r=d.discover(apk,out)
            self.assertEqual(r['shield_ui']['files'][0]['path'],'assets/monkey/NewGUI/Common/ShieldAnims.uih')
            self.assertIn('BadgeStyle1',r['shield_ui']['tokens'])
            rec=next(x for x in r['atlas_symbols'] if x['name']=='MapShieldDesign7')
            self.assertEqual(rec['atlas'],'UIAtlas2')
            self.assertEqual(rec['box'],[100,200,164,264])
            self.assertEqual(rec['key_path'],'assets/monkey/UI/packed-images.dat')
            self.assertEqual(r['clubs']['fields'][2],'homestyle')
            self.assertEqual(r['clubs']['samples']['3141']['shortname'],'Besiktas')


if __name__=='__main__': unittest.main()
