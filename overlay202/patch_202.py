from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    field='''    private String onlineConversationTopic="";
    private long onlineConversationTopicAt=0L;
'''
    newfield='''    private String onlineConversationTopic="";
    private long onlineConversationTopicAt=0L;
    private String jarvisMediaProvider="";
    private long jarvisMediaAt=0L;
'''
    if field not in s: raise SystemExit(name+': media field marker missing')
    s=s.replace(field,newfield,1)

    dispatch='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;
        long onlineTopicAge='''
    owner='HybridActivity' if name=='HybridActivity.java' else 'JarvisHomeActivity'
    newdispatch=f'''    private void dispatch(String raw){{
        String jarvisOriginalRaw=raw;

        long jarvisMediaAge=jarvisMediaAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisMediaAt);
        final MediaCommandRouter.Command jarvisMediaCommand=MediaCommandRouter.parse(raw,jarvisMediaProvider,jarvisMediaAge);
        if(jarvisMediaCommand!=null){{
            onlineConversationTopic="";
            onlineConversationTopicAt=0L;
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;

            boolean jarvisMediaNeedsApp=jarvisMediaCommand.action.equals("PLAY")
                ||jarvisMediaCommand.action.equals("SEARCH")
                ||jarvisMediaCommand.action.equals("OPEN");

            if(jarvisMediaNeedsApp&&!MediaActions.providerInstalled(this,jarvisMediaCommand.provider)){{
                String missing=MediaCommandRouter.providerName(jarvisMediaCommand.provider)+" yüklü değil efendim.";
                if(answer!=null)answer.setText(missing);
                if(meta!=null)meta.setText("Media Entity 4.0 · uygulama bulunamadı");
                if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
                if(voice!=null)voice.beginTurn();
                final Runnable done=new Runnable(){{public void run(){{
                    if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                    WakeWordService.resume({owner}.this,"media_missing");
                }}}};
                say(missing,"",done);
                return;
            }}

            jarvisMediaProvider=jarvisMediaCommand.provider;
            jarvisMediaAt=android.os.SystemClock.elapsedRealtime();

            if(answer!=null)answer.setText(jarvisMediaCommand.reply);
            if(meta!=null)meta.setText("Media Entity 4.0 · "+MediaCommandRouter.providerName(jarvisMediaCommand.provider)+" · "+jarvisMediaCommand.action);
            if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+jarvisMediaCommand.reply);
            if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+jarvisMediaCommand.reply);
            if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+jarvisMediaCommand.reply);
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Yanıtlıyorum...");
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
            if(voice!=null)voice.beginTurn();

            say(jarvisMediaCommand.reply,"",new Runnable(){{public void run(){{
                try{{
                    MediaActions.execute({owner}.this,jarvisMediaCommand);
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                }}catch(Exception e){{
                    if(answer!=null)answer.setText("Medya işlemi tamamlanamadı.");
                    if(meta!=null)meta.setText("Media Entity 4.0 · işlem başarısız · "+e.getClass().getSimpleName());
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Medya işlemi başarısız.");
                }}
                if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                WakeWordService.resume({owner}.this,"media_done");
            }}}});
            return;
        }}

        long onlineTopicAge='''
    if dispatch not in s: raise SystemExit(name+': dispatch media insertion marker missing')
    s=s.replace(dispatch,newdispatch,1)

    current='''        View n201=jarvisReleaseCard("JARVIS 2.0.1","ONLINE FOLLOW-UP CONTEXT",'''
    replacement='''        View n202=jarvisReleaseCard("JARVIS 2.0.2","MEDIA ENTITY 4.0",
            "• Spotify, YouTube ve YouTube Music için ayrı medya komut yönlendiricisi eklendi.\n• Sanatçı + şarkı sorguları sağlayıcıya medya arama/oynatma intent'i olarak gönderilir.\n• 'Nilüfer’i Müslüm’den aç' ve 'Müslüm’den Nilüfer çal' gibi sanatçı/şarkı ayrımı desteklenir.\n• Son kullanılan medya sağlayıcısı 30 dakika tutulur; 'durdur', 'devam et', 'sonraki', 'önceki' kısa komutları bağlama göre çalışır.\n• Spotify/YouTube uygulaması yoksa JARVIS işlem yapılmış gibi davranmaz.\n• 'Spotify’ı kapat' üçüncü parti uygulamayı force-stop etmek yerine gerçek medya oynatmasını durdurur.",true);
        View n201=jarvisReleaseCard("JARVIS 2.0.1","ONLINE FOLLOW-UP CONTEXT",'''
    if current not in s: raise SystemExit(name+': release 201 marker missing')
    s=s.replace(current,replacement,1)

    # Demote previous current card.
    marker='''• Offline komut motoru ve 1.9.9 Contextual Commands önceliği korunur.",true);'''
    if marker in s:
        s=s.replace(marker,'''• Offline komut motoru ve 1.9.9 Contextual Commands önceliği korunur.",false);''',1)

    s=s.replace('View[] cards={n201,n200,n199,n198,n197,n196,n195,n164};',
                'View[] cards={n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)
    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_201";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_202";',1)

    s=s.replace('JARVIS 2.0.1  •  FOLLOW-UP CONTEXT','JARVIS 2.0.2  •  MEDIA ENTITY 4.0',1)
    s=s.replace('JARVIS 2.0.1  •  build 123','JARVIS 2.0.2  •  build 124',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.1','JARVIS  •  ELITE INTERFACE  •  2.0.2',1)

    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="124" android:versionName="2.0.2"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 124',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.2'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.2 Media Entity 4.0 patch applied')
