#!/usr/bin/env python3
import json
import sys
from pathlib import Path

ANCHOR='''    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v13, 0xf
    rem-int/2addr v12, v13
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
'''

OVERRIDE='''    iget v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_id:I
    const/16 v13, 0xc45
    if-ne v12, v13, :nss_reborn_badge_check_3157
    const/16 v12, 0x10
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I
    goto :nss_reborn_badge_done

    :nss_reborn_badge_check_3157
    const/16 v13, 0xc55
    if-ne v12, v13, :nss_reborn_badge_done
    const/16 v12, 0x11
    iput v12, v4, Lcom/newstargames/newstarsoccer/c_TClub;->m_badgestyle:I

    :nss_reborn_badge_done
'''


def patch_smali_text(text):
    count=text.count(ANCHOR)
    if count!=1:
        raise ValueError(f'stock badge-style anchor expected once, got {count}')
    if ':nss_reborn_badge_done' in text:
        raise ValueError('badge override already present')
    out=text.replace(ANCHOR,ANCHOR+OVERRIDE,1)
    report={
        'anchor_count':count,
        'fallback':'m_id % 15',
        'overrides':{'3141':16,'3157':17},
        'stock_anchor_preserved':ANCHOR in out,
        'inserted_label':'nss_reborn_badge_done',
    }
    return out,report


def main():
    if len(sys.argv)!=4:
        raise SystemExit(f'usage: {sys.argv[0]} IN.smali OUT.smali REPORT.json')
    src,dst,report=map(Path,sys.argv[1:])
    text=src.read_text(encoding='utf-8')
    out,meta=patch_smali_text(text)
    dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(out,encoding='utf-8')
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    print('CLUB_BADGE_OVERRIDE_PATCH=PASS fallback=id%15 overrides=3141:16,3157:17')

if __name__=='__main__': main()
