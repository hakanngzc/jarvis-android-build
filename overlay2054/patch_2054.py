from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    old_profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_LARGE_DOUBLE_MOTION_CRASHFIX_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2053";'''
    new_profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_HYPER_MOTION_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2054";'''
    if old_profile not in s:
        raise SystemExit(name+': 2.0.5.3 profile marker missing')
    s=s.replace(old_profile,new_profile,1)

    marker='''        View n2053=jarvisReleaseCard("JARVIS 2.0.5.3","LARGE CORE CRASH HOTFIX",'''
    if marker not in s:
        raise SystemExit(name+': 2.0.5.3 release marker missing')

    s=s.replace(marker,
'''        View n2054=jarvisReleaseCard("JARVIS 2.0.5.4","HYPER MOTION CORE",
            "• Çekirdek 356dp büyük boyutta kalır.\\n• Ana orbit sayısı 6'dan 10'a çıkarıldı.\\n• Aura parçacıkları 20'den 36'ya yükseltildi.\\n• 3 pulse shell, 4 kinetic ring, 6 scanner kolu ve 12 halo node eklendi.\\n• Nucleus uyduları 4'ten 8'e çıkarıldı; elektron kuyrukları uzatıldı.\\n• 2× animasyon hızı korunurken tüm katmanlar tek Canvas renderer içinde çalışır.\\n• Komut/Cevap paneli gizli kalır; 2.0.5.3 crash fix korunur.",true);
        View n2053=jarvisReleaseCard("JARVIS 2.0.5.3","LARGE CORE CRASH HOTFIX",''',1)

    idx=s.find('View n2053=jarvisReleaseCard("JARVIS 2.0.5.3"')
    end=s.find('",true);',idx)
    if idx<0 or end<0:
        raise SystemExit(name+': 2.0.5.3 current card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s:
        raise SystemExit(name+': release cards marker missing')
    s=s.replace(cards,'View[] cards={n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 2.0.5.3  •  LARGE CORE','JARVIS 2.0.5.4  •  HYPER MOTION',1)
    s=s.replace('JARVIS 2.0.5.3  •  build 134','JARVIS 2.0.5.4  •  build 135',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.5.3','JARVIS  •  ELITE INTERFACE  •  2.0.5.4',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="135" android:versionName="2.0.5.4"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 135',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.5.4'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.5.4 Hyper Motion Core patch applied')
