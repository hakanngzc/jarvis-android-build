#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from dex_inventory import build
EXPECTED_SUBSYSTEMS={'android_resources':18,'career_player':58,'cloud_social_commerce':242,'competition_world':40,'data_config':136,'debug_dev':16,'game_domain_other':934,'input_controls':37,'match_engine':117,'media_assets':205,'monkey_framework':258,'persistence_bootstrap':52,'platform_bridge_other':12,'platform_lifecycle':36,'third_party_platform_bridges':22,'ui_framework':46,'utility_core':426}
BASE_SHA='46b5577b464b35c7122c3cf9737c6a7887ae28bb0911c7687b8b433ea6880aa4'
CLASSMAP_SHA='06ee8bea2f3c406b7d19ade0f6c2b4d4b6a070f5500e838938a3d89e779a8ae8'
OWNER_SHA='c24fc96e01a5e41aae440f07f63f39c74fb98a231abb35cd19463dbbcc215937'
PROFILE={'NSS_EMULATOR_API':'29','NSS_EMULATOR_TARGET':'default','NSS_EMULATOR_ARCH':'x86_64','NSS_EMULATOR_PROFILE':'pixel_4','NSS_EMULATOR_CORES':'2','NSS_EMULATOR_RAM':'2048M','NSS_EMULATOR_HEAP':'384M','NSS_EMULATOR_KVM_REQUIRED':'1'}

def main():
    if len(sys.argv)!=2: raise SystemExit('usage: verify_deep_foundation.py BASE_APK')
    d=build(Path(sys.argv[1]))
    assert d['apk_sha256']==BASE_SHA,d['apk_sha256']
    assert d['app_classes']==2747
    assert d['screen_classes']==92
    assert d['non_screen_classes']==2655
    assert d['subsystem_counts']==EXPECTED_SUBSYSTEMS
    assert d['classmap_sha256']==CLASSMAP_SHA,d['classmap_sha256']
    assert d['owners']==730
    assert d['static_fields']==8890
    assert d['owner_counts_sha256']==OWNER_SHA,d['owner_counts_sha256']
    strings=set(d['strings']); classes=set(d['classes'])
    for token in ('.monkeystate','gxtkAppState','m_gameversion','getPreferences','onWindowFocusChanged','p_OnSuspend','p_OnResume'):
        assert token in strings,token
    for cls in ('MonkeyGame','AndroidGame','BBAndroidGame','c_GameDelegate','c_GameEngine','c_TPlayer','c_TMatch','c_TCompetition','c_TFixture','c_TClub'):
        assert cls in classes,cls
    env={}
    for line in (Path(__file__).with_name('emulator_profile.env')).read_text().splitlines():
        if line and not line.startswith('#'):
            k,v=line.split('=',1);env[k]=v
    for k,v in PROFILE.items(): assert env.get(k)==v,(k,env.get(k),v)
    assert env['NSS_EMULATOR_TARGET']!='google_apis'
    print('VERDICT=STAGE0_PUBLIC_STOCK_DEX_INVENTORY_PASS')
    print('app_classes=2747 screen_classes=92 non_screen_classes=2655 static_owners=730 static_fields=8890')
    print('VERDICT=STAGE0_PUBLIC_SAVE_LIFECYCLE_IDENTIFIERS_PASS')
    print('prefs=.monkeystate legacy=gxtkAppState version_field=m_gameversion lifecycle=focus/suspend/resume')
    print('VERDICT=STAGE0_PUBLIC_EMULATOR_PROFILE_PASS')
if __name__=='__main__': main()
