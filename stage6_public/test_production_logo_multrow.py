import unittest

from production_logo_pipeline import atlas_records_for_append


class ProductionLogoMultirowTests(unittest.TestCase):
    def test_render_data_carries_both_u_and_v_bounds(self):
        manifest={
            'version':1,'cell_size':128,
            'clubs':[
                {'club_id':100+i,'style':16+i,'symbol':f'Club{100+i}','asset':f'{100+i}.png'}
                for i in range(4)
            ],
        }
        records=atlas_records_for_append(manifest,atlas_width=256,atlas_height=256)
        self.assertEqual(records[0]['render_data'],[0.0,1.0,0.0,0.5,1.0,0.0,0.5,0.0])
        self.assertEqual(records[1]['render_data'],[0.0,1.0,0.5,0.5,1.0,0.0,1.0,0.0])
        self.assertEqual(records[2]['render_data'],[0.0,1.0,0.0,1.0,1.0,0.0,0.5,0.5])
        self.assertEqual(records[3]['render_data'],[0.0,1.0,0.5,1.0,1.0,0.0,1.0,0.5])


if __name__=='__main__': unittest.main()
