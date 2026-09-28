from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    state_marker='''    private String jarvisConversationTopic="";
    private long jarvisConversationLastAt=0L;
'''
    state_new='''    private String jarvisConversationTopic="";
    private long jarvisConversationLastAt=0L;
    private String jarvisLastActionCommand="";
    private long jarvisLastActionAt=0L;
'''
    if state_marker not in s: raise SystemExit(name+': state marker missing')
    s=s.replace(state_marker,state_new,1)

    dispatch_marker='    private void dispatch(String raw){if(jarvisTryDailyConversation(raw))return;'
    dispatch_new='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;
        long jarvisActionAge=jarvisLastActionAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisLastActionAt);
        ContextCommandResolver.Resolution jarvisContextResolution=ContextCommandResolver.resolve(raw,jarvisLastActionCommand,jarvisActionAge);
        if(jarvisContextResolution!=null&&jarvisContextResolution.confidence>=88){
            raw=jarvisContextResolution.resolvedCommand;
        }

        if(jarvisTryDailyConversation(raw)){
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;
            return;
        }

        if(ContextCommandResolver.isTrackable(raw)){
            jarvisLastActionCommand=raw==null?"":raw.trim();
            jarvisLastActionAt=android.os.SystemClock.elapsedRealtime();
        }else if(jarvisContextResolution==null){
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;
        }
'''
    if dispatch_marker not in s: raise SystemExit(name+': dispatch marker missing')
    s=s.replace(dispatch_marker,dispatch_new,1)

    # Keep the original spoken/typed follow-up visible, while execution uses the resolved full command.
    ui_marker='''        if(jarvisOverlayCommandLine!=null)jarvisOverlayCommandLine.setText("Komut: "+(q.length()==0?"—":q));'''
    # no changes needed inside conversation path

    # Changelog: 1.9.9 becomes current, older current badge is demoted.
    s=s.replace('''        View n198=jarvisReleaseCard("JARVIS 1.9.8","CONTEXT MEMORY + CHANGELOG",
            "• Oturum içi isim ve konu hafızası eklendi.\\n• Kısa devam cümleleri daha doğal bağlama bağlandı.\\n• Sağ panele Sürüm Notları bölümü eklendi.\\n• Ayarlar ve panel sürüm bilgileri güncellendi.\\n• Komut kalkanı korunarak alarm, uygulama ve cihaz komutlarının sohbet tarafından yakalanması engellendi.",true);''',
'''        View n199=jarvisReleaseCard("JARVIS 1.9.9","CONTEXTUAL COMMAND ENGINE",
            "• Son güvenli cihaz komutu 90 saniye boyunca bağlam olarak tutulur.\\n• Ses komutlarında 'biraz daha', 'geri al', 'tekrar yap' devamları eklendi.\\n• Fener için 'kapat', 'geri aç' gibi kısa devam komutları eklendi.\\n• Spotify ve YouTube açma komutları güvenli biçimde tekrar edilebilir.\\n• Göreli alarmda '5 dakika daha ekle', '10 dakika azalt', 'tekrar kur' desteği eklendi.\\n• Arama ve mesaj gibi hassas eylemler tekrar bağlamına özellikle alınmadı.",true);
        View n198=jarvisReleaseCard("JARVIS 1.9.8","CONTEXT MEMORY + CHANGELOG",
            "• Oturum içi isim ve konu hafızası eklendi.\\n• Kısa devam cümleleri daha doğal bağlama bağlandı.\\n• Sağ panele Sürüm Notları bölümü eklendi.\\n• Ayarlar ve panel sürüm bilgileri güncellendi.\\n• Komut kalkanı korunarak alarm, uygulama ve cihaz komutlarının sohbet tarafından yakalanması engellendi.",false);''',1)

    s=s.replace('View[] cards={n198,n197,n196,n195,n164};','View[] cards={n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 1.9.8  •  CONTEXT MEMORY','JARVIS 1.9.9  •  CONTEXT COMMANDS',1)
    s=s.replace('JARVIS 1.9.8  •  build 120','JARVIS 1.9.9  •  build 121',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  1.9.8','JARVIS  •  ELITE INTERFACE  •  1.9.9',1)

    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="121" android:versionName="1.9.9"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 121',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.9.9'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 1.9.9 contextual command engine patch applied')
