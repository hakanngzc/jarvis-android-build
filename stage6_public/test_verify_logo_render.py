import unittest
from PIL import Image, ImageDraw

from verify_logo_render import analyze_image, render_passes


def make_frame():
    w,h=1080,2280
    im=Image.new('RGB',(w,h),(246,233,210))
    d=ImageDraw.Draw(im)
    # Deliberately use a shifted/non-640 viewport so fixed logical crops fail.
    d.rectangle((35,470,805,1510),fill=(255,249,237),outline=(38,53,74),width=9)
    # Club 3141 identity: black/white + red.
    d.rounded_rectangle((85,575,340,925),radius=35,fill=(245,245,240),outline=(20,20,25),width=14)
    for x in (120,170,220,270): d.rectangle((x,600,x+24,900),fill=(20,20,25))
    d.ellipse((165,690,250,775),fill=(238,52,52))
    # Club 3157 identity: yellow + blue.
    d.ellipse((500,580,750,920),fill=(250,205,35),outline=(20,65,170),width=18)
    d.rectangle((520,700,730,790),fill=(20,65,170))
    d.ellipse((605,720,655,770),fill=(238,52,52))
    # Stock fallback shield below both custom marks.
    d.ellipse((330,1080,505,1325),fill=(238,238,235),outline=(38,53,74),width=12)
    d.polygon([(342,1100),(420,1090),(415,1310),(345,1300)],fill=(38,53,74))
    return im


class LogoRenderVerifierTests(unittest.TestCase):
    def test_accepts_shifted_multi_logo_frame_without_640_coordinate_assumption(self):
        m=analyze_image(make_frame())
        self.assertTrue(render_passes(m),m)
        self.assertGreater(m['club3141_red'],0.005)
        self.assertGreater(m['club3157_yellow'],0.01)
        self.assertGreater(m['club3157_blue'],0.01)
        self.assertGreater(m['stock_stddev'],12.0)

    def test_rejects_blank_cream_frame(self):
        m=analyze_image(Image.new('RGB',(1080,2280),(246,233,210)))
        self.assertFalse(render_passes(m),m)


if __name__=='__main__': unittest.main()
