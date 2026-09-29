from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')
    owner='HybridActivity' if name=='HybridActivity.java' else 'JarvisHomeActivity'

    field='''    private String jarvisContactFlow="";
    private ContactCommandRouter.Command jarvisPendingContactCommand=null;
    private ContactActions.ResolvedContact jarvisPendingResolvedContact=null;
'''
    newfield='''    private String jarvisContactFlow="";
    private ContactCommandRouter.Command jarvisPendingContactCommand=null;
    private ContactActions.ResolvedContact jarvisPendingResolvedContact=null;
    private String jarvisBrainIntent="UNKNOWN";
    private int jarvisBrainConfidence=0;
    private SemanticCommandBrain.Resolution jarvisSemanticPending=null;
    private long jarvisSemanticPendingAt=0L;
    private boolean jarvisSemanticBypass=false;
'''
    if field not in s:
        raise SystemExit(name+': intelligence field marker missing')
    s=s.replace(field,newfield,1)

    dispatch='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;
'''
    dispatch_new='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;
        BrainEngine.Result jarvisBrain=BrainEngine.analyze(raw);
        jarvisBrainIntent=jarvisBrain.intent;
        jarvisBrainConfidence=jarvisBrain.confidence;
        if(jarvisContactFlow.length()==0 && jarvisBrain.rewritten && !jarvisBrain.protectedFreeText){
            raw=jarvisBrain.routedCommand;
        }
'''
    if dispatch not in s:
        raise SystemExit(name+': dispatch marker missing')
    s=s.replace(dispatch,dispatch_new,1)

    marker='''        long onlineTopicAge='''
    semantic=f'''        if(!jarvisSemanticBypass){{
            long semanticAge=jarvisSemanticPendingAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisSemanticPendingAt);
            if(jarvisSemanticPending!=null&&semanticAge<=30000L){{
                if(SemanticCommandBrain.yes(raw)){{
                    final String canonical=jarvisSemanticPending.canonicalCommand;
                    jarvisSemanticPending=null;
                    jarvisSemanticPendingAt=0L;
                    jarvisSemanticBypass=true;
                    try{{dispatch(canonical);}}finally{{jarvisSemanticBypass=false;}}
                    return;
                }}
                if(SemanticCommandBrain.no(raw)){{
                    jarvisSemanticPending=null;
                    jarvisSemanticPendingAt=0L;
                    final String cancelled="Tamam efendim, işlemi iptal ettim.";
                    if(answer!=null)answer.setText(cancelled);
                    if(meta!=null)meta.setText("Brain Engine 1.0 · semantic confirmation cancelled");
                    if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+cancelled);
                    if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+cancelled);
                    if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+cancelled);
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Yanıtlıyorum...");
                    if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
                    if(voice!=null)voice.beginTurn();
                    say(cancelled,"",new Runnable(){{public void run(){{
                        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                        if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                        WakeWordService.resume({owner}.this,"semantic_cancel");
                    }}}});
                    return;
                }}
            }}else if(jarvisSemanticPending!=null){{
                jarvisSemanticPending=null;
                jarvisSemanticPendingAt=0L;
            }}

            final SemanticCommandBrain.Resolution semantic=SemanticCommandBrain.resolve(raw);
            if(semantic!=null){{
                if(semantic.autoExecute()){{
                    if(meta!=null)meta.setText("Brain Engine 1.0 · "+semantic.intent+" · confidence "+semantic.confidence);
                    jarvisSemanticBypass=true;
                    try{{dispatch(semantic.canonicalCommand);}}finally{{jarvisSemanticBypass=false;}}
                    return;
                }}
                if(semantic.needsConfirmation()){{
                    jarvisSemanticPending=semantic;
                    jarvisSemanticPendingAt=android.os.SystemClock.elapsedRealtime();
                    final String ask=SemanticCommandBrain.confirmationText(semantic);
                    if(answer!=null)answer.setText(ask);
                    if(meta!=null)meta.setText("Brain Engine 1.0 · confirmation · "+semantic.intent+" · confidence "+semantic.confidence);
                    if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+ask);
                    if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+ask);
                    if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+ask);
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Onay bekliyorum...");
                    if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
                    if(voice!=null)voice.beginTurn();
                    say(ask,"",new Runnable(){{public void run(){{
                        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                        WakeWordService.resume({owner}.this,"semantic_confirm");
                    }}}});
                    return;
                }}
            }}
        }}

        long onlineTopicAge='''
    if marker not in s:
        raise SystemExit(name+': semantic insertion marker missing')
    s=s.replace(marker,semantic,1)

    known='''        boolean known=pc!=null
            ||jarvisContactFlow.length()>0
            ||ContactCommandRouter.parse(top,jarvisLastContactTarget,contactKnownAge)!=null
            ||DeviceCommandRouter.parse(top)!=null'''
    known_new='''        boolean known=pc!=null
            ||jarvisContactFlow.length()>0
            ||jarvisSemanticPending!=null
            ||ContactCommandRouter.parse(top,jarvisLastContactTarget,contactKnownAge)!=null
            ||SemanticCommandBrain.resolve(top)!=null
            ||DeviceCommandRouter.parse(top)!=null'''
    if known not in s:
        raise SystemExit(name+': semantic known-intent marker missing')
    s=s.replace(known,known_new,1)

    profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_SMOOTH_VOICE_FOCUS_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2055";'''
    profile_new='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_SMOOTH_VOICE_FOCUS_V1";
    private static final String JARVIS_INTELLIGENCE_PROFILE="INTELLIGENCE_CORE_STAGE1_V1";
    private static final String JARVIS_BRAIN_PROFILE="BRAIN_ENGINE_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_206";'''
    if profile not in s:
        raise SystemExit(name+': 2.0.5.5 profile marker missing')
    s=s.replace(profile,profile_new,1)

    release='''        View n2055=jarvisReleaseCard("JARVIS 2.0.5.5","SMOOTH VOICE FOCUS",'''
    if release not in s:
        raise SystemExit(name+': 2.0.5.5 release marker missing')
    s=s.replace(release,
'''        View n206=jarvisReleaseCard("JARVIS 2.0.6","BRAIN ENGINE 1.0",
            "• BrainEngine komutlardan önce çalışır; ASR hatalarını düzeltir, temel entity çıkarır ve 0–100 güven skoru üretir.\\n• 'blutut', 'vayfay', 'spotifay', 'alaram' gibi sık ses tanıma hataları güvenli şekilde kanonik komuta çevrilir.\\n• Yerel intent similarity fallback cihaz/medya/app ifadelerinde tam kalıp dışındaki yakın söyleyişleri yakalar.\\n• Semantic Command Brain korunur: 88+ confidence otomatik, 70–87 confidence sesli evet/hayır onayı, daha düşük güven işlem yapmaz.\\n• Alarm, kişi arama, mesaj ve web sorguları semantic tahmine kapalı kalır.\\n• WhatsApp/SMS serbest mesaj metni BrainEngine tarafından değiştirilmez.\\n• 2.0.5.5 Smooth Voice Focus, Hyper Motion, Spotify, Contact Intelligence ve tüm önceki motorlar korunur.",true);
        View n2055=jarvisReleaseCard("JARVIS 2.0.5.5","SMOOTH VOICE FOCUS",''',1)

    idx=s.find('View n2055=jarvisReleaseCard("JARVIS 2.0.5.5"')
    end=s.find('",true);',idx)
    if idx<0 or end<0:
        raise SystemExit(name+': current 2.0.5.5 card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2055,n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s:
        raise SystemExit(name+': release cards marker missing')
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

print('JARVIS 2.0.6 Brain Engine + Semantic Confidence Gate patch applied')
