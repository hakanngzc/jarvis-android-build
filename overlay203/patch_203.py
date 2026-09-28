from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')
    owner='HybridActivity' if name=='HybridActivity.java' else 'JarvisHomeActivity'

    marker='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;

        long jarvisMediaAge='''
    insert=f'''    private void dispatch(String raw){{
        String jarvisOriginalRaw=raw;

        final DeviceCommandRouter.Command jarvisDeviceCommand=DeviceCommandRouter.parse(raw);
        if(jarvisDeviceCommand!=null){{
            onlineConversationTopic="";
            onlineConversationTopicAt=0L;
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;

            if(answer!=null)answer.setText(jarvisDeviceCommand.reply);
            if(meta!=null)meta.setText("Device Control 1.0 · "+jarvisDeviceCommand.action);
            if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+jarvisDeviceCommand.reply);
            if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+jarvisDeviceCommand.reply);
            if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+jarvisDeviceCommand.reply);
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Cihaz kontrolü uygulanıyor...");
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
            if(voice!=null)voice.beginTurn();

            final Runnable deviceDone=new Runnable(){{public void run(){{
                if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                WakeWordService.resume({owner}.this,"device_control_done");
            }}}};

            say(jarvisDeviceCommand.reply,"",new Runnable(){{public void run(){{
                try{{
                    DeviceActions.Result result=DeviceActions.execute({owner}.this,jarvisDeviceCommand);
                    if(result.panelOpened){{
                        final String fallback=DeviceActions.fallbackVoice(jarvisDeviceCommand);
                        if(answer!=null)answer.setText(fallback);
                        if(meta!=null)meta.setText("Device Control 1.0 · sistem paneli fallback · "+jarvisDeviceCommand.action);
                        if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+fallback);
                        if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+fallback);
                        if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+fallback);
                        say(fallback,"",deviceDone);
                        return;
                    }}
                    deviceDone.run();
                }}catch(Exception e){{
                    final String failed="Cihaz kontrolü tamamlanamadı efendim.";
                    if(answer!=null)answer.setText(failed);
                    if(meta!=null)meta.setText("Device Control 1.0 · işlem başarısız · "+e.getClass().getSimpleName());
                    if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+failed);
                    if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+failed);
                    if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+failed);
                    say(failed,"",deviceDone);
                }}
            }}}});
            return;
        }}

        long jarvisMediaAge='''
    if marker not in s:
        raise SystemExit(name+': device dispatch marker missing')
    s=s.replace(marker,insert,1)

    release='''        View n2024=jarvisReleaseCard("JARVIS 2.0.2.4","SPOTIFY OAUTH + EXACT TRACK URI",'''
    newrelease='''        View n203=jarvisReleaseCard("JARVIS 2.0.3","DEVICE CONTROL ENGINE",
            "• Bluetooth aç/kapat sesli komutları eklendi.\\n• Wi-Fi aç/kapat sesli komutları eklendi.\\n• 'Açık mı?' durum sorguları özellikle bu sürüme eklenmedi.\\n• targetSdk 28 uyumluluk yolunda Android izin verirse Bluetooth ve Wi-Fi doğrudan değiştirilir.\\n• Android veya cihaz üreticisi doğrudan değişikliği engellerse JARVIS başarı uydurmaz; ilgili sistem kontrol ekranını açar ve bunu sesli söyler.\\n• Spotify OAuth, Exact Track URI, MediaSession, wake word, alarm ve hibrit çekirdek korunur.",true);
        View n2024=jarvisReleaseCard("JARVIS 2.0.2.4","SPOTIFY OAUTH + EXACT TRACK URI",'''
    if release not in s:
        raise SystemExit(name+': release 2.0.2.4 marker missing')
    s=s.replace(release,newrelease,1)

    idx=s.find('View n2024=jarvisReleaseCard("JARVIS 2.0.2.4"')
    end=s.find('",true);',idx)
    if idx<0 or end<0:
        raise SystemExit(name+': current 2.0.2.4 card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s:
        raise SystemExit(name+': release card list marker missing')
    s=s.replace(cards,'View[] cards={n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2024";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_203";',1)
    s=s.replace('JARVIS 2.0.2.4  •  SPOTIFY OAUTH','JARVIS 2.0.3  •  DEVICE CONTROL',1)
    s=s.replace('JARVIS 2.0.2.4  •  build 128','JARVIS 2.0.3  •  build 129',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.2.4','JARVIS  •  ELITE INTERFACE  •  2.0.3',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
permissions=[
    '<uses-permission android:name="android.permission.BLUETOOTH" />',
    '<uses-permission android:name="android.permission.BLUETOOTH_ADMIN" />',
    '<uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />',
    '<uses-permission android:name="android.permission.CHANGE_WIFI_STATE" />'
]
for permission in permissions:
    if permission not in x:
        pos=x.find('<application')
        if pos<0: raise SystemExit('manifest application marker missing')
        x=x[:pos]+permission+'\n    '+x[pos:]

x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="129" android:versionName="2.0.3"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 129',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.3'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.3 Device Control Engine patch applied')
