#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path


def verify(base, post, restart, meta):
    stable = ('sdate','clubnationid','clubid','fullname','shortname','careerapps','goalbonus','wage','lastnegotiations','lasttransferdate','playerrecordsha256','clubrecordsha256','competitionrecordsha256','additionalclubrecordsha256')
    checks = {
        'minimum_match_cycles': int(meta['natural_match_cycles']) >= int(meta['minimum_match_cycles']),
        'minimum_progress_days': int(post['sdate']) - int(base['sdate']) >= int(meta['minimum_progress_days']),
        'long_wall_time': int(meta['wall_seconds']) >= int(meta['minimum_wall_seconds']),
        'newseason_setup1': bool(meta['NewSeasonSetUp1']),
        'newseason_setup2': bool(meta['NewSeasonSetUp2']),
        'newseason_setup3': bool(meta['NewSeasonSetUp3']),
        'newseason_setup4': bool(meta['NewSeasonSetUp4']),
        'nss_crash_or_anr_absent': not bool(meta['nss_crash_or_anr']),
        'restart_reload_equivalent': all(post.get(k)==restart.get(k) for k in stable),
    }
    return {'checks':checks,'pass':all(checks.values()),'base_sdate':base['sdate'],'post_sdate':post['sdate']}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--base',type=Path,required=True); ap.add_argument('--post',type=Path,required=True); ap.add_argument('--restart',type=Path,required=True); ap.add_argument('--meta',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); load=lambda p:json.loads(p.read_text(encoding='utf-8'))
    result=verify(load(a.base),load(a.post),load(a.restart),load(a.meta)); a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(result,sort_keys=True))
    if not result['pass']: raise SystemExit(1)
    print('STAGE4_NATURAL_SEASON_PASS')
if __name__=='__main__': main()
