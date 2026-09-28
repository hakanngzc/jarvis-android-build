from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

follow_method=r'''    private boolean jarvisTryOnlineFollowup(final String raw){
        if(onlineIntelligenceLastAnswer==null)return false;
        long age=onlineIntelligenceLastAnswerAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-onlineIntelligenceLastAnswerAt);
        final OnlineFollowupRouter.Followup f=OnlineFollowupRouter.match(
            raw,
            onlineIntelligenceLastAnswer.title,
            onlineIntelligenceLastAnswer.text,
            onlineIntelligenceLastAnswer.source,
            onlineIntelligenceLastAnswer.url,
            age);
        if(f==null)return false;

        if(voice!=null)voice.beginTurn();
        if(answer!=null)answer.setText(f.text);
        if(meta!=null){
            String source=onlineIntelligenceLastAnswer.source==null?"":onlineIntelligenceLastAnswer.source;
            meta.setText("Online Intelligence · bağlamsal takip\nKaynak: "+source);
            if(!f.openSource){
                final String link=onlineIntelligenceLastAnswer.url;
                meta.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
                    try{if(link!=null&&link.startsWith("https://"))startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(link)));}catch(Exception ignored){}
                }});
            }
        }
        if(retry!=null)retry.setVisibility(View.VISIBLE);
        if(jarvisReadyLine!=null)jarvisReadyLine.setText("Yanıtlıyorum...");
        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);

        Runnable action=null;
        if(f.openSource){
            final String link=onlineIntelligenceLastAnswer.url;
            action=new Runnable(){public void run(){
                try{
                    if(link!=null&&link.startsWith("https://"))startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(link)));
                }catch(Exception ignored){}
            }};
        }
        say(f.text,"",action);
        if(jarvisAtomCore!=null)jarvisAtomCore.postDelayed(new Runnable(){public void run(){
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
        }},900L);
        return true;
    }

'''

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    field='''    private String onlineIntelligenceLastQuery="";
'''
    field_new='''    private String onlineIntelligenceLastQuery="";
    private OnlineIntelligenceEngine.Answer onlineIntelligenceLastAnswer;
    private long onlineIntelligenceLastAnswerAt=0L;
'''
    if field not in s: raise SystemExit(name+': online field marker missing')
    s=s.replace(field,field_new,1)

    method_marker='    private void jarvisRequestOnlineIntelligence(final String raw){'
    if method_marker not in s: raise SystemExit(name+': online request method marker missing')
    s=s.replace(method_marker,follow_method+method_marker,1)

    success='''                    if(cancel!=null)cancel.setVisibility(View.GONE);
                    if(answer!=null)answer.setText(a.title+"\n\n"+a.text);'''
    success_new='''                    if(cancel!=null)cancel.setVisibility(View.GONE);
                    onlineIntelligenceLastAnswer=a;
                    onlineIntelligenceLastAnswerAt=android.os.SystemClock.elapsedRealtime();
                    if(answer!=null)answer.setText(a.title+"\n\n"+a.text);'''
    if success not in s: raise SystemExit(name+': online success marker missing')
    s=s.replace(success,success_new,1)

    dispatch='''        if(jarvisTryDailyConversation(raw)){
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;
            return;
        }
'''
    dispatch_new='''        if(jarvisTryOnlineFollowup(jarvisOriginalRaw)){
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;
            return;
        }

        if(jarvisTryDailyConversation(raw)){
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;
            return;
        }
'''
    if dispatch not in s: raise SystemExit(name+': dispatch conversation marker missing')
    s=s.replace(dispatch,dispatch_new,1)

    clear='engine.clearCache();if(onlineIntelligence!=null)onlineIntelligence.clearCache();handler.post'
    clear_new='engine.clearCache();if(onlineIntelligence!=null)onlineIntelligence.clearCache();onlineIntelligenceLastAnswer=null;onlineIntelligenceLastAnswerAt=0L;handler.post'
    if clear in s:s=s.replace(clear,clear_new,1)

    settings='''        jarvisAddSettingsCard(content,jarvisSettingsInfo("Online Intelligence","Anahtarsız bilgi fallback'i  •  DDG + Türkçe Wikipedia","◎"));'''
    settings_new='''        jarvisAddSettingsCard(content,jarvisSettingsInfo("Online Intelligence","Natural Query V2  •  DDG + Türkçe Wikipedia","◎"));'''
    if settings not in s: raise SystemExit(name+': online settings marker missing')
    s=s.replace(settings,settings_new,1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_200";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_201";',1)

    anchor='''        View n200=jarvisReleaseCard("JARVIS 2.0.0","ONLINE INTELLIGENCE LAYER",
'''
    if anchor not in s: raise SystemExit(name+': release 200 anchor missing')
    n201='''        View n201=jarvisReleaseCard("JARVIS 2.0.1","NATURAL ONLINE FOLLOW-UP",
            "• Doğal bilgi soru kalıpları genişletildi: 'bana anlat', 'açıkla', 'ne işe yarar', 'neden önemli' ve karşılaştırma soruları.\n• Son çevrimiçi yanıt 3 dakika boyunca konuşma bağlamında tutulur.\n• 'biraz daha anlat', 'kısaca söyle', 'tekrar söyle' takip komutları eklendi.\n• 'kaynağın ne?' sorusuna kaynak adıyla yanıt verilir.\n• 'kaynağı aç' komutu önce sesli geri dönüş yapıp ardından güvenli HTTPS kaynağını açar.\n• Online takip cümleleri yeni arama sanılmaz; mevcut yanıt bağlamından çözülür.",true);
'''
    s=s.replace(anchor,n201+anchor,1)

    # Demote 2.0.0 current badge only inside its card.
    old_end='''            "• Canlı haber, skor, borsa ve benzeri zaman hassas sorgular bilinçli olarak bu ilk sürümde kapsama alınmadı.",true);'''
    new_end='''            "• Canlı haber, skor, borsa ve benzeri zaman hassas sorgular bilinçli olarak bu ilk sürümde kapsama alınmadı.",false);'''
    if old_end not in s: raise SystemExit(name+': release 200 badge marker missing')
    s=s.replace(old_end,new_end,1)

    cards='View[] cards={n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': release cards marker missing')
    s=s.replace(cards,'View[] cards={n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 2.0.0  •  ONLINE INTELLIGENCE','JARVIS 2.0.1  •  NATURAL ONLINE',1)
    s=s.replace('JARVIS 2.0.0  •  build 122','JARVIS 2.0.1  •  build 123',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.0','JARVIS  •  ELITE INTERFACE  •  2.0.1',1)

    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="123" android:versionName="2.0.1"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 123',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.1'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.1 natural online follow-up patch applied')
