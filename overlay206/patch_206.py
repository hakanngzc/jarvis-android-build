from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    marker='''    private String jarvisLastContactTarget="";
    private long jarvisLastContactAt=0L;
'''
    if marker not in s:
        raise SystemExit(name+': brain field marker missing')
    s=s.replace(marker,marker+'''    private String jarvisBrainIntent="UNKNOWN";
    private int jarvisBrainConfidence=0;
''',1)

    dispatch='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;
'''
    if dispatch not in s:
        raise SystemExit(name+': dispatch marker missing')
    s=s.replace(dispatch,dispatch+'''        BrainEngine.Result jarvisBrain=BrainEngine.analyze(raw);
        jarvisBrainIntent=jarvisBrain.intent;
        jarvisBrainConfidence=jarvisBrain.confidence;
        if(jarvisContactFlow.length()==0 && jarvisBrain.rewritten && !jarvisBrain.protectedFreeText){
            raw=jarvisBrain.routedCommand;
        }
''',1)

    old_profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_SMOOTH_VOICE_FOCUS_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2055";'''
    new_profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_SMOOTH_VOICE_FOCUS_V1";
    private static final String JARVIS_BRAIN_PROFILE="BRAIN_ENGINE_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_206";'''
    if old_profile not in s:
        raise SystemExit(name+': 2.0.5.5 profile marker missing')
    s=s.replace(old_profile,new_profile,1)

    marker2='''        View n2055=jarvisReleaseCard("JARVIS 2.0.5.5","SMOOTH VOICE FOCUS",'''
    if marker2 not in s:
        raise SystemExit(name+': release marker missing')
    s=s.replace(marker2,
'''        View n206=jarvisReleaseCard("JARVIS 2.0.6","BRAIN ENGINE 1.0",
            "• Yeni BrainEngine bütün komutlardan önce çalışır; mevcut uzman motorların üstüne güvenli bir ön-anlama katmanı ekler.\\n• ASR Correction 1.0: 'blutut', 'vayfay', 'spotifay', 'alaram' gibi sık ses tanıma hatalarını düzeltir.\\n• Confidence Engine 1.0: her komuta 0–100 güven skoru verir; düşük güvenli komutları zorla dönüştürmez.\\n• Turkish Entity 2.0: sağlayıcı, kişi hedefi ve göreli süre gibi temel entity'leri ayırır.\\n• Local Intent Similarity 1.0: tam kalıp eşleşmezse cihaz/medya/app komutlarında yerel benzerlik fallback'i kullanır.\\n• Serbest WhatsApp/SMS mesaj gövdesi korunur; BrainEngine mesaj içeriğini otomatik değiştirmez.\\n• 2.0.5.5 Smooth Voice Focus, Hyper Motion, alarm, Spotify, cihaz, app ve Contact Intelligence korunur.",true);
        View n2055=jarvisReleaseCard("JARVIS 2.0.5.5","SMOOTH VOICE FOCUS",''',1)

    idx=s.find('View n2055=jarvisReleaseCard("JARVIS 2.0.5.5"')
    end=s.find('",true);',idx)
    if idx<0 or end<0:
        raise SystemExit(name+': current card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2055,n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s:
        raise SystemExit(name+': cards marker missing')
    s=s.replace(cards,'View[] cards={n206,n2055,n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 2.0.5.5  •  SMOOTH VOICE FOCUS','JARVIS 2.0.6  •  BRAIN ENGINE 1.0',1)
    s=s.replace('JARVIS 2.0.5.5  •  build 136','JARVIS 2.0.6  •  build 137',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.5.5','JARVIS  •  ELITE INTERFACE  •  2.0.6',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="137" android:versionName="2.0.6"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 137',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.6'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.6 Brain Engine 1.0 patch applied')
