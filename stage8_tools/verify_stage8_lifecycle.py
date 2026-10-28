#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from stage3_tools.stage2_checkpoint import extract_checkpoint, extract_monkeystate_from_prefs_xml

STABLE_FIELDS=(
    'sdate','clubnationid','clubid','fullname','shortname','careerapps',
    'goalbonus','wage','lastnegotiations','lasttransferdate',
    'clubrecordsha256','competitionrecordsha256','additionalclubrecordsha256',
)

def checkpoint_from_xml(path: str|Path):
    text=Path(path).read_text(encoding='utf-8',errors='replace')
    return extract_checkpoint(extract_monkeystate_from_prefs_xml(text),0)

def compare_checkpoints(pre,post):
    errors=[]
    for key in STABLE_FIELDS:
        if pre.get(key)!=post.get(key):
            errors.append(f'{key}: {pre.get(key)!r} -> {post.get(key)!r}')
    return {'ok':not errors,'errors':errors,'stable_fields':list(STABLE_FIELDS)}

def main():
    if len(sys.argv)!=3: raise SystemExit('usage: verify_stage8_lifecycle.py PRE_XML POST_XML')
    pre=checkpoint_from_xml(sys.argv[1]); post=checkpoint_from_xml(sys.argv[2]); result=compare_checkpoints(pre,post)
    print('NSS REBORN — STAGE8 CAREER LIFECYCLE VERIFICATION')
    for key in STABLE_FIELDS:
        ok=pre.get(key)==post.get(key)
        print(('PASS' if ok else 'FAIL')+f' {key}: {pre.get(key)!r} -> {post.get(key)!r}')
    for e in result['errors']: print('FAIL '+e)
    print('VERDICT='+('CAREER_LIFECYCLE_PASS' if result['ok'] else 'CAREER_LIFECYCLE_FAIL'))
    if not result['ok']: raise SystemExit(1)
if __name__=='__main__': main()
