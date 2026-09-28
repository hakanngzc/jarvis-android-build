from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    old='    private static final String JARVIS_CONVERSATION_PROFILE="CONVERSATION_CORE_V1";\n'
    new='''    private static final String JARVIS_CONVERSATION_PROFILE="CONTEXT_TALK_V2";
    private String jarvisConversationLastIntent="";
    private String jarvisConversationLastUser="";
    private String jarvisConversationLastAnswer="";
    private long jarvisConversationLastAt=0L;
'''
    if old not in s:
        raise SystemExit(name+': conversation profile marker missing')
    s=s.replace(old,new,1)

    old_call='        ConversationRouter.Reply reply=ConversationRouter.match(raw);'
    new_call='''        long jarvisConversationAge=jarvisConversationLastAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisConversationLastAt);
        ConversationRouter.Reply reply=ConversationRouter.matchContext(raw,jarvisConversationLastIntent,jarvisConversationLastUser,jarvisConversationLastAnswer,jarvisConversationAge);'''
    if old_call not in s:
        raise SystemExit(name+': router call marker missing')
    s=s.replace(old_call,new_call,1)

    old_answer='        String answer=reply.text==null?"":reply.text.trim();'
    new_answer='''        String answer=reply.text==null?"":reply.text.trim();
        jarvisConversationLastIntent=reply.intent==null?"":reply.intent;
        jarvisConversationLastUser=q;
        jarvisConversationLastAnswer=answer;
        jarvisConversationLastAt=android.os.SystemClock.elapsedRealtime();'''
    if old_answer not in s:
        raise SystemExit(name+': answer marker missing')
    s=s.replace(old_answer,new_answer,1)

    s=s.replace('JARVIS  •  ELITE INTERFACE  •  1.9.6','JARVIS  •  ELITE INTERFACE  •  1.9.7')
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="119" android:versionName="1.9.7"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 119',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.9.7'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 1.9.7 context talk patch applied')
