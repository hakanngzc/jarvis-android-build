#!/usr/bin/env python3
import json
import sys
from pathlib import Path

from PIL import Image, ImageStat


def _ratio(img,target,tol=24):
    total=max(1,img.width*img.height)
    hit=0
    for p in img.getdata():
        if max(abs(p[i]-target[i]) for i in range(3))<=tol:
            hit+=1
    return hit/total


def analyze_image(image):
    im=image.convert('RGB')
    w,h=im.size
    # NSS 4.31 can letterbox/offset its logical UI viewport. Use broad,
    # relative identity zones instead of assuming logical width 640 maps to
    # the physical screenshot width.
    left=im.crop((0,int(h*.14),int(w*.48),int(h*.48)))
    right=im.crop((int(w*.38),int(h*.14),int(w*.82),int(h*.48)))
    stock=im.crop((int(w*.18),int(h*.38),int(w*.62),int(h*.64)))
    return {
        'width':w,'height':h,
        'club3141_red':_ratio(left,(238,52,52)),
        'club3141_dark':_ratio(left,(20,20,25)),
        'club3141_yellow':_ratio(left,(250,205,35)),
        'club3157_yellow':_ratio(right,(250,205,35)),
        'club3157_blue':_ratio(right,(20,65,170)),
        'club3157_dark':_ratio(right,(20,20,25)),
        'stock_navy':_ratio(stock,(38,53,74),35),
        'stock_stddev':sum(ImageStat.Stat(stock).stddev)/3.0,
    }


def render_passes(m):
    return (
        m['club3141_red']>0.005 and
        m['club3141_dark']>0.02 and
        m['club3141_red']>m['club3141_yellow']*2+0.002 and
        m['club3157_yellow']>0.01 and
        m['club3157_blue']>0.01 and
        m['stock_stddev']>12.0 and
        m['stock_navy']>0.002
    )


def verify_file(image_path,report_path):
    m=analyze_image(Image.open(image_path))
    m['pass']=render_passes(m)
    Path(report_path).write_text('\n'.join(f'{k}={v}' for k,v in m.items())+'\n',encoding='utf-8')
    print(' '.join(f'{k}={v}' for k,v in m.items()))
    return m


def main():
    if len(sys.argv)!=3:
        raise SystemExit(f'usage: {sys.argv[0]} SCREENSHOT.png REPORT.txt')
    m=verify_file(sys.argv[1],sys.argv[2])
    raise SystemExit(0 if m['pass'] else 1)


if __name__=='__main__': main()
