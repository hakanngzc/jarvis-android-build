from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

helper=r'''    private boolean jarvisTryDailyConversation(String raw){
        ConversationRouter.Reply reply=ConversationRouter.match(raw);
        if(reply==null)return false;

        String q=raw==null?"":raw.replace("\\n"," ").replaceAll("\\s+"," ").trim();
        String answer=reply.text==null?"":reply.text.trim();

        if(jarvisOverlayCommandLine!=null)jarvisOverlayCommandLine.setText("Komut: "+(q.length()==0?"—":q));
        if(jarvisCommandLine!=null)jarvisCommandLine.setText("Komut: "+(q.length()==0?"—":q));
        if(jarvisWriteCommandLine!=null)jarvisWriteCommandLine.setText("SEN  •  "+(q.length()==0?"—":q));

        if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+answer);
        if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+answer);
        if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+answer);
        if(jarvisWriteStatusLine!=null)jarvisWriteStatusLine.setText("Yanıt alındı");
        if(jarvisReadyLine!=null)jarvisReadyLine.setText("Yanıtlıyorum...");
        jarvisQueueHistory(q,answer);

        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
        if(voice!=null)voice.beginTurn();

        final Runnable done=new Runnable(){public void run(){
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
            if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
            WakeWordService.resume(JarvisHomeActivity.this,"conversation_done");
        }};

        say(answer,reply.voiceKey,done);
        return true;
    }

'''

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    marker='    private void dispatch(String raw){'
    if marker not in s:
        raise SystemExit(name+': dispatch marker missing')

    class_name=name[:-5]
    local_helper=helper.replace('JarvisHomeActivity.this',class_name+'.this')
    if 'CONVERSATION_CORE_V1' not in s:
        inject='    private static final String JARVIS_CONVERSATION_PROFILE="CONVERSATION_CORE_V1";\n'+local_helper
        s=s.replace(marker,inject+marker,1)

    # Conversation router gets first refusal. Non-conversation commands fall through unchanged.
    marker2='    private void dispatch(String raw){'
    if marker2+'if(jarvisTryDailyConversation(raw))return;' not in s:
        s=s.replace(marker2,marker2+'if(jarvisTryDailyConversation(raw))return;',1)

    s=s.replace('JARVIS  •  ELITE INTERFACE  •  1.9.5','JARVIS  •  ELITE INTERFACE  •  1.9.6')
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="118" android:versionName="1.9.6"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 118',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.9.6'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 1.9.6 conversation core patch applied')
