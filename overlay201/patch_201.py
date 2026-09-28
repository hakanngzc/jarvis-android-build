from pathlib import Path
import sys,re
base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
 p=java/name
 s=p.read_text(encoding='utf-8')

 field='''    private String onlineIntelligenceLastQuery="";
'''
 newfield='''    private String onlineIntelligenceLastQuery="";
    private String onlineConversationTopic="";
    private long onlineConversationTopicAt=0L;
'''
 if field not in s: raise SystemExit(name+': online field marker missing')
 s=s.replace(field,newfield,1)

 dispatch='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;'''
 newdispatch='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;
        long onlineTopicAge=onlineConversationTopicAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-onlineConversationTopicAt);
        String onlineExpanded=OnlineConversationContext.expand(raw,onlineConversationTopic,onlineTopicAge);
        if(onlineExpanded!=null){
            jarvisRequestOnlineIntelligence(onlineExpanded);
            return;
        }'''
 if dispatch not in s: raise SystemExit(name+': dispatch marker missing')
 s=s.replace(dispatch,newdispatch,1)

 success='''                    if(answer!=null)answer.setText(a.title+"\\n\\n"+a.text);'''
 successnew='''                    if(answer!=null)answer.setText(a.title+"\\n\\n"+a.text);
                    onlineConversationTopic=OnlineConversationContext.topicFromAnswer(a.title,query);
                    onlineConversationTopicAt=android.os.SystemClock.elapsedRealtime();'''
 if success not in s: raise SystemExit(name+': online success marker missing')
 s=s.replace(success,successnew,1)

 # If a real trackable device action begins, do not let old online topic leak into later followups.
 action='''        if(ContextCommandResolver.isTrackable(raw)){
            jarvisLastActionCommand=raw==null?"":raw.trim();'''
 actionnew='''        if(ContextCommandResolver.isTrackable(raw)){
            onlineConversationTopic="";
            onlineConversationTopicAt=0L;
            jarvisLastActionCommand=raw==null?"":raw.trim();'''
 if action not in s: raise SystemExit(name+': action marker missing')
 s=s.replace(action,actionnew,1)

 old='''        View n200=jarvisReleaseCard("JARVIS 2.0.0","ONLINE INTELLIGENCE LAYER",
            "• Tanınmayan güvenli bilgi soruları için çevrimiçi fallback eklendi.\n• Wikimedia tabanlı Türkçe Wikipedia arama ve özet kaynakları anahtarsız kullanılır.\n• Cihaz, alarm, uygulama ve medya komutları online fallback'ten tamamen ayrıldı.\n• Çevrimiçi yanıtlar kaynak, alınma zamanı ve tıklanabilir kaynak bağlantısıyla gösterilir.\n• Yanıtlar cihazda önbelleğe alınır; çevrimdışıyken daha önce alınmış bilgi kullanılabilir.\n• Canlı haber, skor, borsa ve benzeri zaman hassas sorgular bilinçli olarak bu ilk sürümde kapsama alınmadı.",true);'''
 new='''        View n201=jarvisReleaseCard("JARVIS 2.0.1","ONLINE FOLLOW-UP CONTEXT",
            "• Online bilgi cevabının konusu 3 dakika boyunca kısa bağlam olarak tutulur.\n• 'Biraz daha anlat', 'devam et', 'peki ne zaman?', 'nerede?', 'neden?' ve 'nasıl?' gibi takip soruları aynı konuya bağlanır.\n• Yeni cihaz komutu başladığında eski online konu bağlamı temizlenir.\n• Takip soruları yine mevcut güvenli Wikipedia + cache altyapısını kullanır.\n• Offline komut motoru ve 1.9.9 Contextual Commands önceliği korunur.",true);
        View n200=jarvisReleaseCard("JARVIS 2.0.0","ONLINE INTELLIGENCE LAYER",
            "• Tanınmayan güvenli bilgi soruları için çevrimiçi fallback eklendi.\n• Wikimedia tabanlı Türkçe Wikipedia arama ve özet kaynakları anahtarsız kullanılır.\n• Cihaz, alarm, uygulama ve medya komutları online fallback'ten tamamen ayrıldı.\n• Çevrimiçi yanıtlar kaynak, alınma zamanı ve tıklanabilir kaynak bağlantısıyla gösterilir.\n• Yanıtlar cihazda önbelleğe alınır; çevrimdışıyken daha önce alınmış bilgi kullanılabilir.\n• Canlı haber, skor, borsa ve benzeri zaman hassas sorgular bilinçli olarak bu ilk sürümde kapsama alınmadı.",false);'''
 if old not in s: raise SystemExit(name+': release 200 marker missing')
 s=s.replace(old,new,1)
 s=s.replace('View[] cards={n200,n199,n198,n197,n196,n195,n164};','View[] cards={n201,n200,n199,n198,n197,n196,n195,n164};',1)
 s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_200";','private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_201";',1)
 s=s.replace('JARVIS 2.0.0  •  ONLINE INTELLIGENCE','JARVIS 2.0.1  •  FOLLOW-UP CONTEXT',1)
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
print('JARVIS 2.0.1 online follow-up context patch applied')
