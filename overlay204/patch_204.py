from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')
    owner='HybridActivity' if name=='HybridActivity.java' else 'JarvisHomeActivity'

    field='''    private String jarvisMediaProvider="";
    private long jarvisMediaAt=0L;
'''
    newfield='''    private String jarvisMediaProvider="";
    private long jarvisMediaAt=0L;
    private String jarvisLastAppTarget="";
    private long jarvisLastAppAt=0L;
'''
    if field not in s: raise SystemExit(name+': app context field marker missing')
    s=s.replace(field,newfield,1)

    marker='''        long onlineTopicAge='''
    insert=f'''        long jarvisAppAge=jarvisLastAppAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisLastAppAt);
        final AppCommandRouter.Command jarvisAppCommand=AppCommandRouter.parse(raw,jarvisLastAppTarget,jarvisAppAge);
        if(jarvisAppCommand!=null){{
            onlineConversationTopic="";
            onlineConversationTopicAt=0L;
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;

            if(answer!=null)answer.setText(jarvisAppCommand.reply);
            if(meta!=null)meta.setText("App Control 1.0 · "+jarvisAppCommand.action+" · "+jarvisAppCommand.target);
            if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+jarvisAppCommand.reply);
            if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+jarvisAppCommand.reply);
            if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+jarvisAppCommand.reply);
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Uygulama komutu uygulanıyor...");
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
            if(voice!=null)voice.beginTurn();

            final Runnable appDone=new Runnable(){{public void run(){{
                if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                WakeWordService.resume({owner}.this,"app_control_done");
            }}}};

            say(jarvisAppCommand.reply,"",new Runnable(){{public void run(){{
                try{{
                    AppActions.Result result=AppActions.execute({owner}.this,jarvisAppCommand);
                    if(result.success){{
                        jarvisLastAppTarget=result.resolvedLabel.length()>0?result.resolvedLabel:jarvisAppCommand.target;
                        jarvisLastAppAt=android.os.SystemClock.elapsedRealtime();
                        appDone.run();
                        return;
                    }}

                    if(result.managementFallback){{
                        jarvisLastAppTarget=result.resolvedLabel.length()>0?result.resolvedLabel:jarvisAppCommand.target;
                        jarvisLastAppAt=android.os.SystemClock.elapsedRealtime();
                        final String msg="Android üçüncü taraf uygulamayı doğrudan kapatmama izin vermiyor efendim. Uygulama yönetimini açtım.";
                        if(answer!=null)answer.setText(msg);
                        if(meta!=null)meta.setText("App Control 1.0 · force-stop engelli · "+result.packageName);
                        if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+msg);
                        if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+msg);
                        if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+msg);
                        say(msg,"",appDone);
                        return;
                    }}

                    final String miss=jarvisAppCommand.target+" uygulamasını bulamadım efendim.";
                    if(answer!=null)answer.setText(miss);
                    if(meta!=null)meta.setText("App Control 1.0 · uygulama bulunamadı");
                    if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+miss);
                    if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+miss);
                    if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+miss);
                    say(miss,"",appDone);
                }}catch(Exception e){{
                    final String failed="Uygulama komutu tamamlanamadı efendim.";
                    if(answer!=null)answer.setText(failed);
                    if(meta!=null)meta.setText("App Control 1.0 · işlem başarısız · "+e.getClass().getSimpleName());
                    if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+failed);
                    if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+failed);
                    if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+failed);
                    say(failed,"",appDone);
                }}
            }}}});
            return;
        }}

        long onlineTopicAge='''
    if marker not in s: raise SystemExit(name+': app dispatch insertion marker missing')
    s=s.replace(marker,insert,1)

    known='''        PhoneCommand pc=PhoneCommand.parse(top);boolean known=pc!=null||HybridEngine.route(CommandLanguage.canonical(top),prefs.getString("city","Kahramanmaraş"))!=null||CommandLanguage.isWake(top)||pendingAlarm.length()>0||pendingConfirmation!=null;'''
    known_new='''        PhoneCommand pc=PhoneCommand.parse(top);
        long mediaKnownAge=jarvisMediaAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisMediaAt);
        long appKnownAge=jarvisLastAppAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisLastAppAt);
        boolean known=pc!=null
            ||DeviceCommandRouter.parse(top)!=null
            ||MediaCommandRouter.parse(top,jarvisMediaProvider,mediaKnownAge)!=null
            ||AppCommandRouter.parse(top,jarvisLastAppTarget,appKnownAge)!=null
            ||HybridEngine.route(CommandLanguage.canonical(top),prefs.getString("city","Kahramanmaraş"))!=null
            ||CommandLanguage.isWake(top)||pendingAlarm.length()>0||pendingConfirmation!=null;'''
    if known not in s: raise SystemExit(name+': speech known marker missing')
    s=s.replace(known,known_new,1)

    release='''        View n203=jarvisReleaseCard("JARVIS 2.0.3","DEVICE CONTROL ENGINE",'''
    newrelease='''        View n204=jarvisReleaseCard("JARVIS 2.0.4","APP CONTROL + NATURAL MEDIA",
            "• Cihazdaki launcher uygulamaları gerçek uygulama etiketine göre dinamik bulunup açılır.\\n• Instagram, WhatsApp, Telegram, Chrome gibi uygulamalar yanında Kamera, Galeri, Ayarlar ve Kişiler için sistem yolları eklendi.\\n• 'Tekrar aç', 'onu aç' gibi kısa uygulama takip komutları 2 dakika bağlam tutar.\\n• Android 14 üçüncü taraf uygulamaları force-stop etmeyi engellediği için 'uygulamayı kapat' sahte başarı vermez; ilgili uygulama yönetim ekranını açar.\\n• 'Devam', 'sonrakine geç', 'bir sonrakine geç', 'öncekine dön' gibi kısa medya komutları sağlayıcı adı olmadan aktif medyayı kontrol eder.\\n• Ses tanıma, Device/Media/App niyetlerini bilinen komut olarak değerlendirir; gereksiz belirsizlik ekranları azaltıldı.\\n• Spotify OAuth + Exact Track URI, Bluetooth/Wi-Fi, alarm, wake word ve hibrit çekirdek korunur.",true);
        View n203=jarvisReleaseCard("JARVIS 2.0.3","DEVICE CONTROL ENGINE",'''
    if release not in s: raise SystemExit(name+': 2.0.3 release marker missing')
    s=s.replace(release,newrelease,1)

    idx=s.find('View n203=jarvisReleaseCard("JARVIS 2.0.3"')
    end=s.find('",true);',idx)
    if idx<0 or end<0: raise SystemExit(name+': current 2.0.3 card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': release card list marker missing')
    s=s.replace(cards,'View[] cards={n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_203";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_204";',1)
    s=s.replace('JARVIS 2.0.3  •  DEVICE CONTROL','JARVIS 2.0.4  •  APP + MEDIA CONTEXT',1)
    s=s.replace('JARVIS 2.0.3  •  build 129','JARVIS 2.0.4  •  build 130',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.3','JARVIS  •  ELITE INTERFACE  •  2.0.4',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="130" android:versionName="2.0.4"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 130',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.4'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.4 App Control + Natural Media patch applied')
