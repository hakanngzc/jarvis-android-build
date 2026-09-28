from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

online_method=r'''    private void jarvisRequestOnlineIntelligence(final String raw){
        if(onlineIntelligence==null||onlineIntelligenceHttp==null)return;
        final String query=OnlineQueryRouter.query(raw);
        cancelWork();
        last=null;
        onlineIntelligenceLastQuery=query;

        if(voice!=null)voice.beginTurn();
        final int id=generation;
        final boolean online=isOnline();

        if(answer!=null)answer.setText(online?"Çevrimiçi bilgi aranıyor…":"Kayıtlı çevrimiçi yanıt aranıyor…");
        if(meta!=null){
            meta.setText("Online Intelligence · güvenli bilgi fallback'i\nYerel ve cihaz komutları önceliklidir.");
            meta.setOnClickListener(null);
        }
        if(retry!=null)retry.setVisibility(View.GONE);
        if(cancel!=null)cancel.setVisibility(View.VISIBLE);
        if(jarvisReadyLine!=null)jarvisReadyLine.setText("İnternetten araştırıyorum...");
        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);

        final Runnable timeout=new Runnable(){public void run(){
            if(dead||generation!=id)return;
            cancelWork();
            if(answer!=null)answer.setText("Çevrimiçi bilgi isteği zaman aşımına uğradı.");
            if(meta!=null)meta.setText("Online Intelligence · zaman aşımı · yerel komutlar aktif");
            if(retry!=null)retry.setVisibility(View.VISIBLE);
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
            say("Çevrimiçi bilgi isteği zaman aşımına uğradı efendim.","",null);
        }};
        handler.postDelayed(timeout,18000);

        pending=worker.submit(new Runnable(){public void run(){
            try{
                final OnlineIntelligenceEngine.Answer a=onlineIntelligence.fetch(query,online,System.currentTimeMillis());
                handler.post(new Runnable(){public void run(){
                    handler.removeCallbacks(timeout);
                    if(dead||generation!=id)return;
                    if(cancel!=null)cancel.setVisibility(View.GONE);
                    if(answer!=null)answer.setText(a.title+"\n\n"+a.text);

                    String date=new SimpleDateFormat("dd.MM.yyyy HH:mm",new Locale("tr","TR")).format(new Date(a.fetchedAt));
                    if(meta!=null){
                        meta.setText((a.cached?"KAYITLI ONLINE YANIT · "+(a.stale?"GÜNCELLİĞİNİ YİTİRMİŞ OLABİLİR":"önbellekten"):"ONLINE INTELLIGENCE")
                            +"\nAlınma: "+date+"\nKaynak: "+a.source+"\nKaynağı açmak için dokunun.");
                        final String link=a.url;
                        meta.setOnClickListener(new View.OnClickListener(){public void onClick(View v){
                            try{startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(link)));}catch(Exception ignored){}
                        }});
                    }
                    if(retry!=null)retry.setVisibility(View.VISIBLE);
                    say(OnlineIntelligenceEngine.speechText(a),"",new Runnable(){public void run(){
                        if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                    }});
                }});
            }catch(final Exception e){
                handler.post(new Runnable(){public void run(){
                    handler.removeCallbacks(timeout);
                    if(dead||generation!=id)return;
                    if(cancel!=null)cancel.setVisibility(View.GONE);
                    String msg=e instanceof OnlineIntelligenceEngine.Unavailable?e.getMessage():"Çevrimiçi bilgi alınamadı.";
                    if(answer!=null)answer.setText(msg);
                    if(meta!=null)meta.setText("Online Intelligence · bilgi uydurulmadı · yerel komutlar aktif");
                    if(retry!=null)retry.setVisibility(View.VISIBLE);
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                    if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                    say(msg+" Efendim.","",null);
                }});
            }
        }});
    }

'''

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    field='    private HybridEngine.HttpsTransport http;\n'
    field_new='''    private HybridEngine.HttpsTransport http;
    private OnlineIntelligenceEngine onlineIntelligence;
    private OnlineIntelligenceEngine.HttpsTransport onlineIntelligenceHttp;
    private String onlineIntelligenceLastQuery="";
'''
    if field not in s: raise SystemExit(name+': hybrid field marker missing')
    s=s.replace(field,field_new,1)

    init='        http=new HybridEngine.HttpsTransport();engine=new HybridEngine(getFilesDir(),http);'
    init_new='''        http=new HybridEngine.HttpsTransport();engine=new HybridEngine(getFilesDir(),http);
        onlineIntelligenceHttp=new OnlineIntelligenceEngine.HttpsTransport();
        onlineIntelligence=new OnlineIntelligenceEngine(getFilesDir(),onlineIntelligenceHttp);'''
    if init not in s: raise SystemExit(name+': engine init marker missing')
    s=s.replace(init,init_new,1)

    cancel='if(http!=null)http.cancel();if(cancel!=null)cancel.setVisibility(View.GONE);'
    cancel_new='if(http!=null)http.cancel();if(onlineIntelligenceHttp!=null)onlineIntelligenceHttp.cancel();if(cancel!=null)cancel.setVisibility(View.GONE);'
    if cancel not in s: raise SystemExit(name+': cancel marker missing')
    s=s.replace(cancel,cancel_new,1)

    retry='retry=button("YENİDEN DENE",new View.OnClickListener(){public void onClick(View v){if(last!=null)request(last);}});'
    retry_new='retry=button("YENİDEN DENE",new View.OnClickListener(){public void onClick(View v){if(last!=null)request(last);else if(onlineIntelligenceLastQuery!=null&&onlineIntelligenceLastQuery.length()>0)jarvisRequestOnlineIntelligence(onlineIntelligenceLastQuery);}});'
    if retry not in s: raise SystemExit(name+': retry marker missing')
    s=s.replace(retry,retry_new,1)

    cache='engine.clearCache();handler.post'
    cache_new='engine.clearCache();if(onlineIntelligence!=null)onlineIntelligence.clearCache();handler.post'
    if cache in s:s=s.replace(cache,cache_new,1)

    request_marker='    private void request(final HybridEngine.Request r){'
    if request_marker not in s: raise SystemExit(name+': request marker missing')
    class_method=online_method
    s=s.replace(request_marker,class_method+request_marker,1)

    request_start='''    private void request(final HybridEngine.Request r){
        if(voice!=null)voice.beginTurn();'''
    request_start_new='''    private void request(final HybridEngine.Request r){
        onlineIntelligenceLastQuery="";
        if(voice!=null)voice.beginTurn();'''
    if request_start not in s: raise SystemExit(name+': request start marker missing')
    s=s.replace(request_start,request_start_new,1)

    legacy='''            String key=VoiceReplies.legacyKey(textAt(2002),textAt(2003),action!=null);
            if(key.equals("not_executed")){answer.setText("Komut tanındı; otomatik işlem uygulanmadı. Çözümlenen hedef yukarıda.");}
            say("",key,(key.equals("clarify")||key.equals("unknown"))?null:action);return;'''
    legacy_new='''            String key=VoiceReplies.legacyKey(textAt(2002),textAt(2003),action!=null);
            if((key.equals("unknown")||key.equals("clarify")||key.equals("not_executed"))&&OnlineQueryRouter.shouldHandle(jarvisOriginalRaw)){
                deferredAction=null;
                jarvisRequestOnlineIntelligence(jarvisOriginalRaw);
                return;
            }
            if(key.equals("not_executed")){answer.setText("Komut tanındı; otomatik işlem uygulanmadı. Çözümlenen hedef yukarıda.");}
            say("",key,(key.equals("clarify")||key.equals("unknown"))?null:action);return;'''
    if legacy not in s: raise SystemExit(name+': legacy fallback marker missing')
    s=s.replace(legacy,legacy_new,1)

    known='''boolean known=pc!=null||HybridEngine.route(CommandLanguage.canonical(top),prefs.getString("city","Kahramanmaraş"))!=null||CommandLanguage.isWake(top)||pendingAlarm.length()>0||pendingConfirmation!=null;'''
    known_new='''boolean known=pc!=null||HybridEngine.route(CommandLanguage.canonical(top),prefs.getString("city","Kahramanmaraş"))!=null||OnlineQueryRouter.shouldHandle(top)||CommandLanguage.isWake(top)||pendingAlarm.length()>0||pendingConfirmation!=null;'''
    if known not in s: raise SystemExit(name+': speech known marker missing')
    s=s.replace(known,known_new,1)

    settings='''        jarvisAddSettingsCard(content,jarvisSettingsInfo("Çalışma Modu","Hibrit  •  çevrimiçi + çevrimdışı","↔"));'''
    settings_new='''        jarvisAddSettingsCard(content,jarvisSettingsInfo("Çalışma Modu","Hibrit  •  çevrimiçi + çevrimdışı","↔"));
        jarvisAddSettingsCard(content,jarvisSettingsInfo("Online Intelligence","Anahtarsız bilgi fallback'i  •  Wikimedia + Türkçe Wikipedia","◎"));'''
    if settings not in s: raise SystemExit(name+': settings system marker missing')
    s=s.replace(settings,settings_new,1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_198";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_200";',1)

    old_n199=r'''        View n199=jarvisReleaseCard("JARVIS 1.9.9","CONTEXTUAL COMMAND ENGINE",
            "• Son güvenli cihaz komutu 90 saniye boyunca bağlam olarak tutulur.\n• Ses komutlarında 'biraz daha', 'geri al', 'tekrar yap' devamları eklendi.\n• Fener için 'kapat', 'geri aç' gibi kısa devam komutları eklendi.\n• Spotify ve YouTube açma komutları güvenli biçimde tekrar edilebilir.\n• Göreli alarmda '5 dakika daha ekle', '10 dakika azalt', 'tekrar kur' desteği eklendi.\n• Arama ve mesaj gibi hassas eylemler tekrar bağlamına özellikle alınmadı.",true);'''
    new_n199=r'''        View n200=jarvisReleaseCard("JARVIS 2.0.0","ONLINE INTELLIGENCE LAYER",
            "• Tanınmayan güvenli bilgi soruları için çevrimiçi fallback eklendi.\n• Wikimedia tabanlı Türkçe Wikipedia arama ve özet kaynakları anahtarsız kullanılır.\n• Cihaz, alarm, uygulama ve medya komutları online fallback'ten tamamen ayrıldı.\n• Çevrimiçi yanıtlar kaynak, alınma zamanı ve tıklanabilir kaynak bağlantısıyla gösterilir.\n• Yanıtlar cihazda önbelleğe alınır; çevrimdışıyken daha önce alınmış bilgi kullanılabilir.\n• Canlı haber, skor, borsa ve benzeri zaman hassas sorgular bilinçli olarak bu ilk sürümde kapsama alınmadı.",true);
        View n199=jarvisReleaseCard("JARVIS 1.9.9","CONTEXTUAL COMMAND ENGINE",
            "• Son güvenli cihaz komutu 90 saniye boyunca bağlam olarak tutulur.\n• Ses komutlarında 'biraz daha', 'geri al', 'tekrar yap' devamları eklendi.\n• Fener için 'kapat', 'geri aç' gibi kısa devam komutları eklendi.\n• Spotify ve YouTube açma komutları güvenli biçimde tekrar edilebilir.\n• Göreli alarmda '5 dakika daha ekle', '10 dakika azalt', 'tekrar kur' desteği eklendi.\n• Arama ve mesaj gibi hassas eylemler tekrar bağlamına özellikle alınmadı.",false);'''
    if old_n199 not in s: raise SystemExit(name+': release note 199 marker missing')
    s=s.replace(old_n199,new_n199,1)

    cards='View[] cards={n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': release cards marker missing')
    s=s.replace(cards,'View[] cards={n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 1.9.9  •  CONTEXT COMMANDS','JARVIS 2.0.0  •  ONLINE INTELLIGENCE',1)
    s=s.replace('JARVIS 1.9.9  •  build 121','JARVIS 2.0.0  •  build 122',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  1.9.9','JARVIS  •  ELITE INTERFACE  •  2.0.0',1)

    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="122" android:versionName="2.0.0"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 122',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.0'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.0 online intelligence layer patch applied')
