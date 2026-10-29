#!/usr/bin/env python3
from __future__ import annotations
import argparse

CASES = {
    'tvdpi': {'api':29,'dpi':213,'density_split':'config.tvdpi.apk','language_split':'config.tr.apk'},
    'xhdpi': {'api':29,'dpi':320,'density_split':'config.xhdpi.apk','language_split':'config.en.apk'},
    'xxhdpi': {'api':34,'dpi':480,'density_split':'config.xxhdpi.apk','language_split':'config.tr.apk'},
    'xxxhdpi': {'api':34,'dpi':640,'density_split':'config.xxxhdpi.apk','language_split':''},
}

def validate_case(name: str, api: int, dpi: int, density_split: str, language_split: str) -> bool:
    if name not in CASES:
        raise ValueError(f'unknown matrix case: {name}')
    got={'api':int(api),'dpi':int(dpi),'density_split':density_split,'language_split':language_split}
    if got != CASES[name]:
        raise ValueError(f'matrix case drift for {name}: expected={CASES[name]} got={got}')
    return True

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('name'); ap.add_argument('api',type=int); ap.add_argument('dpi',type=int)
    ap.add_argument('density_split'); ap.add_argument('language_split')
    a=ap.parse_args()
    validate_case(a.name,a.api,a.dpi,a.density_split,a.language_split)
    print(f'STAGE6_DENSITY_MATRIX_CONTRACT=PASS case={a.name}')

if __name__=='__main__': main()
