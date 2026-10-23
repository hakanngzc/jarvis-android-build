#!/usr/bin/env python3
import json
import sys
import xml.etree.ElementTree as ET
from decimal import Decimal,InvalidOperation
from pathlib import Path

EXPECTED={
    5:'61.25',6:'62.5',7:'63.75',8:'64.5',9:'65.25',10:'66.5',
    11:'17.25',12:'18.5',33:'77',34:'321',35:'4321',68:'7',69:'3',
    71:'71',72:'72',73:'73',74:'74',75:'75',576:'5',581:'12344',582:'12345',
}


def extract_state(path):
    root=ET.parse(path).getroot()
    for e in root.findall('string'):
        if e.get('name')=='.monkeystate':
            return e.text or ''
    raise ValueError('.monkeystate not found')


def extract_player_tokens(path,slot=0):
    if slot not in (0,1,2): raise ValueError(f'unsupported slot: {slot}')
    state=extract_state(path)
    blocks=state.split(';')
    idx=slot*5+1
    if idx>=len(blocks) or not blocks[idx]:
        raise ValueError(f'player block missing for slot {slot}: block={idx} blocks={len(blocks)}')
    return blocks[idx].split(',')


def _numeric_equal(actual,expected):
    try: return Decimal(actual)==Decimal(expected)
    except (InvalidOperation,ValueError): return actual==expected


def verify_expected(tokens,expected=EXPECTED):
    max_idx=max(expected)
    if len(tokens)<=max_idx:
        raise ValueError(f'player block too short: tokens={len(tokens)} need_index={max_idx}')
    values={str(i):tokens[i] for i in sorted(expected)}
    mismatches={str(i):{'expected':str(expected[i]),'actual':tokens[i]}
                for i in sorted(expected) if not _numeric_equal(tokens[i],str(expected[i]))}
    return {'pass':not mismatches,'token_count':len(tokens),'values':values,'mismatches':mismatches}


def compare_expected(before,after,expected=EXPECTED):
    rb=verify_expected(before,expected); ra=verify_expected(after,expected)
    changed={str(i):{'before':before[i],'after':after[i]}
             for i in sorted(expected) if not _numeric_equal(before[i],after[i])}
    return {'pass':rb['pass'] and ra['pass'] and not changed,'before':rb,'after':ra,'changed':changed}


def main():
    if len(sys.argv) not in (3,4):
        raise SystemExit(f'usage: {sys.argv[0]} BEFORE.xml [AFTER.xml] REPORT.json')
    if len(sys.argv)==3:
        before,report=sys.argv[1:]; result=verify_expected(extract_player_tokens(before))
    else:
        before,after,report=sys.argv[1:]
        result=compare_expected(extract_player_tokens(before),extract_player_tokens(after))
    Path(report).parent.mkdir(parents=True,exist_ok=True)
    Path(report).write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('STAGE7_PLAYER_TOKENS='+('PASS' if result['pass'] else 'FAIL'),f'report={report}')
    if not result['pass']: raise SystemExit(1)


if __name__=='__main__': main()
