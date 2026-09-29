from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    old_profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_HYPER_MOTION_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2054";'''
    new_profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_SMOOTH_VOICE_FOCUS_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2055";'''
    if old_profile not in s:
        raise SystemExit(name+': 2.0.5.4 profile marker missing')
    s=s.replace(old_profile,new_profile,1)

    old_delay='''                        jarvisAtomCore.postDelayed(new Runnable(){public void run(){
                            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                        }},1800L);'''
    new_delay='''                        final long jarvisVoiceFocusDuration=Math.max(1800L,Math.min(7200L,900L+(long)v.length()*55L));
                        jarvisAtomCore.postDelayed(new Runnable(){public void run(){
                            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                        }},jarvisVoiceFocusDuration);'''
    if old_delay not in s:
        raise SystemExit(name+': voice focus delay marker missing')
    s=s.replace(old_delay,new_delay,1)

    marker='''        View n2054=jarvisReleaseCard("JARVIS 2.0.5.4","HYPER MOTION CORE",'''
    if marker not in s:
        raise SystemExit(name+': 2.0.5.4 release marker missing')
    s=s.replace(marker,
'''        View n2055=jarvisReleaseCard("JARVIS 2.0.5.5","SMOOTH VOICE FOCUS",
            "• Hyper Motion görsel katmanları korunurken trigonometrik hesaplar lookup table ile optimize edildi.\\n• Aura ve nucleus gradientleri her karede yeniden üretilmek yerine boyut değişiminde cache edilir.\\n• postInvalidateOnAnimation ile frame zamanlaması Android render döngüsüne bağlandı.\\n• JARVIS konuşurken çekirdeğin tamamı canlı %4–8 zoom/pulse yapar ve ek voice-focus enerji yayları görünür.\\n• Konuşma efekti sabit 1.8 saniye yerine cevap uzunluğuna göre yaklaşık 1.8–7.2 saniye sürer.\\n• 356dp çekirdek, 10 orbit ve Hyper Motion yoğunluğu korunur; Komut/Cevap paneli gizli kalır.",true);
        View n2054=jarvisReleaseCard("JARVIS 2.0.5.4","HYPER MOTION CORE",''',1)

    idx=s.find('View n2054=jarvisReleaseCard("JARVIS 2.0.5.4"')
    end=s.find('",true);',idx)
    if idx<0 or end<0:
        raise SystemExit(name+': current 2.0.5.4 card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s:
        raise SystemExit(name+': release cards marker missing')
    s=s.replace(cards,'View[] cards={n2055,n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 2.0.5.4  •  HYPER MOTION','JARVIS 2.0.5.5  •  SMOOTH VOICE FOCUS',1)
    s=s.replace('JARVIS 2.0.5.4  •  build 135','JARVIS 2.0.5.5  •  build 136',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.5.4','JARVIS  •  ELITE INTERFACE  •  2.0.5.5',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="136" android:versionName="2.0.5.5"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 136',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.5.5'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.5.5 Smooth Voice Focus patch applied')
