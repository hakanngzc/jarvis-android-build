from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

release_methods=r'''    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_198";

    private View jarvisReleaseCard(String version,String stage,String notes,boolean latest){
        LinearLayout card=new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(jarvisDp(14),jarvisDp(12),jarvisDp(14),jarvisDp(12));
        card.setBackground(jarvisBg(latest?0xff072033:0xff06131f,latest?0xff259ee2:0xff173f5b,18));

        LinearLayout head=new LinearLayout(this);
        head.setOrientation(LinearLayout.HORIZONTAL);
        head.setGravity(Gravity.CENTER_VERTICAL);
        TextView v=jarvisText(version,16,latest?0xff8bdcff:0xffedf8fd);
        v.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        if(android.os.Build.VERSION.SDK_INT>=21)v.setLetterSpacing(0.04f);
        head.addView(v,new LinearLayout.LayoutParams(0,jarvisDp(28),1f));
        TextView tag=jarvisText(latest?"GÜNCEL":stage,10,latest?0xffdff8ff:0xff6f9ab6);
        tag.setPadding(jarvisDp(8),0,jarvisDp(8),0);
        tag.setBackground(jarvisBg(latest?0xff0b4568:0xff0a1d2a,latest?0xff2fa9ed:0xff174766,12));
        head.addView(tag,new LinearLayout.LayoutParams(-2,jarvisDp(24)));
        card.addView(head,new LinearLayout.LayoutParams(-1,jarvisDp(30)));

        TextView s=jarvisText(stage,11,0xff5f91b2);
        s.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        card.addView(s,new LinearLayout.LayoutParams(-1,jarvisDp(24)));

        TextView body=jarvisText(notes,13,0xffb8d4e5);
        body.setGravity(Gravity.LEFT);
        body.setLineSpacing(0f,1.12f);
        body.setPadding(0,jarvisDp(5),0,0);
        card.addView(body,new LinearLayout.LayoutParams(-1,-2));
        return card;
    }

    private void jarvisShowReleaseNotes(){
        LinearLayout content=new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(jarvisDp(16),jarvisDp(16),jarvisDp(16),jarvisDp(18));
        content.setBackground(jarvisBg(0xff020a12,0xff155d8a,26));

        LinearLayout intro=jarvisEliteSection("CHANGELOG","Sürüm Notları","JARVIS'e eklenen özellikleri ve altyapı değişikliklerini buradan takip et.");
        LinearLayout.LayoutParams introLp=new LinearLayout.LayoutParams(-1,-2);
        introLp.bottomMargin=jarvisDp(12);content.addView(intro,introLp);

        View n198=jarvisReleaseCard("JARVIS 1.9.8","CONTEXT MEMORY + CHANGELOG",
            "• Oturum içi isim ve konu hafızası eklendi.\n• Kısa devam cümleleri daha doğal bağlama bağlandı.\n• Sağ panele Sürüm Notları bölümü eklendi.\n• Ayarlar ve panel sürüm bilgileri güncellendi.\n• Komut kalkanı korunarak alarm, uygulama ve cihaz komutlarının sohbet tarafından yakalanması engellendi.",true);
        View n197=jarvisReleaseCard("JARVIS 1.9.7","CONTEXT TALK V2",
            "• 3 dakikalık kısa konuşma bağlamı.\n• 'sen?', 'tamam', 'peki', 'mesela' gibi devam cümleleri.\n• Günlük konuşma kapsamı genişletildi.\n• Eylem komutları için koruma katmanı eklendi.",false);
        View n196=jarvisReleaseCard("JARVIS 1.9.6","CONVERSATION CORE V1",
            "• Günlük konuşma çekirdeği eklendi.\n• Selamlaşma, hal hatır, kimlik, teşekkür ve hazır olma diyalogları.\n• Wake-only 'Jarvis' çağrısına doğal geri dönüş.\n• Mevcut komut motoruna dokunmadan sohbet yönlendirme.",false);
        View n195=jarvisReleaseCard("JARVIS 1.9.5","ELITE UI PHASE 8B",
            "• Sağ yan panel daha kompakt hale getirildi.\n• Atom çekirdeği animasyonu ve derinlik hissi geliştirildi.\n• Ana ekran sade tutulurken sohbet, yazı ve ayarlar yan panele taşındı.",false);
        View n164=jarvisReleaseCard("JARVIS 1.6.4.x","HYBRID ENGINE",
            "• Çevrimiçi + çevrimdışı hibrit çalışma altyapısı.\n• Alarm ve telefon komutlarında geniş regresyon testleri.\n• İki adımlı komut zinciri ve göreli alarm ayrımı.\n• İşlemden önce sesli geri dönüş düzeni.",false);

        View[] cards={n198,n197,n196,n195,n164};
        for(View card:cards){
            LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);
            lp.bottomMargin=jarvisDp(10);content.addView(card,lp);
        }

        android.widget.ScrollView scroll=new android.widget.ScrollView(this);
        scroll.setFillViewport(true);
        scroll.addView(content,new android.widget.ScrollView.LayoutParams(-1,-2));
        jarvisOpenElitePage("SÜRÜM NOTLARI","JARVIS değişiklik geçmişi",scroll);
    }

'''

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    old='''    private String jarvisConversationLastIntent="";
    private String jarvisConversationLastUser="";
    private String jarvisConversationLastAnswer="";
    private long jarvisConversationLastAt=0L;
'''
    new='''    private String jarvisConversationLastIntent="";
    private String jarvisConversationLastUser="";
    private String jarvisConversationLastAnswer="";
    private String jarvisConversationName="";
    private String jarvisConversationTopic="";
    private long jarvisConversationLastAt=0L;
'''
    if old not in s: raise SystemExit(name+': conversation state marker missing')
    s=s.replace(old,new,1)

    old_call='ConversationRouter.matchContext(raw,jarvisConversationLastIntent,jarvisConversationLastUser,jarvisConversationLastAnswer,jarvisConversationAge)'
    new_call='ConversationRouter.matchContext(raw,jarvisConversationLastIntent,jarvisConversationLastUser,jarvisConversationLastAnswer,jarvisConversationAge,jarvisConversationName,jarvisConversationTopic)'
    if old_call not in s: raise SystemExit(name+': context call marker missing')
    s=s.replace(old_call,new_call,1)

    old_mem='''        jarvisConversationLastIntent=reply.intent==null?"":reply.intent;
        jarvisConversationLastUser=q;
        jarvisConversationLastAnswer=answer;
        jarvisConversationLastAt=android.os.SystemClock.elapsedRealtime();'''
    new_mem='''        jarvisConversationLastIntent=reply.intent==null?"":reply.intent;
        jarvisConversationLastUser=q;
        jarvisConversationLastAnswer=answer;
        if(reply.memoryName!=null)jarvisConversationName=reply.memoryName;
        if(reply.memoryTopic!=null)jarvisConversationTopic=reply.memoryTopic;
        jarvisConversationLastAt=android.os.SystemClock.elapsedRealtime();'''
    if old_mem not in s: raise SystemExit(name+': memory update marker missing')
    s=s.replace(old_mem,new_mem,1)

    marker='    private View jarvisDrawerItem(String icon,String label,String description,final int action){'
    if marker not in s: raise SystemExit(name+': drawer item marker missing')
    s=s.replace(marker,release_methods+marker,1)

    old_actions='''            if(action==1)jarvisShowChatHistory();
            else if(action==2)jarvisShowWritePanel();
            else if(action==3)jarvisShowSettingsPanel();'''
    new_actions='''            if(action==1)jarvisShowChatHistory();
            else if(action==2)jarvisShowWritePanel();
            else if(action==3)jarvisShowSettingsPanel();
            else if(action==4)jarvisShowReleaseNotes();'''
    if old_actions not in s: raise SystemExit(name+': drawer action marker missing')
    s=s.replace(old_actions,new_actions,1)

    old_menu='''        View chat=jarvisDrawerItem("◌","Sohbet Geçmişi","Önceki komut ve cevaplarını görüntüle",1);
        View write=jarvisDrawerItem("✎","Yaz","JARVIS'e klavyeden komut gönder",2);
        View settings=jarvisDrawerItem("⚙","Ayarlar","Ses, wake word ve uygulama tercihleri",3);

        LinearLayout.LayoutParams menuCardLp=new LinearLayout.LayoutParams(-1,jarvisDp(70));
        menuCardLp.bottomMargin=jarvisDp(10);
        jarvisDrawer.addView(chat,menuCardLp);
        LinearLayout.LayoutParams menuCardLp2=new LinearLayout.LayoutParams(-1,jarvisDp(70));
        menuCardLp2.bottomMargin=jarvisDp(10);
        jarvisDrawer.addView(write,menuCardLp2);
        jarvisDrawer.addView(settings,new LinearLayout.LayoutParams(-1,jarvisDp(70)));'''
    new_menu='''        View chat=jarvisDrawerItem("◌","Sohbet Geçmişi","Önceki komut ve cevaplarını görüntüle",1);
        View write=jarvisDrawerItem("✎","Yaz","JARVIS'e klavyeden komut gönder",2);
        View settings=jarvisDrawerItem("⚙","Ayarlar","Ses, wake word ve uygulama tercihleri",3);
        View releaseNotes=jarvisDrawerItem("i","Sürüm Notları","Bu sürümde neler değiştiğini görüntüle",4);

        LinearLayout.LayoutParams menuCardLp=new LinearLayout.LayoutParams(-1,jarvisDp(64));
        menuCardLp.bottomMargin=jarvisDp(7);
        jarvisDrawer.addView(chat,menuCardLp);
        LinearLayout.LayoutParams menuCardLp2=new LinearLayout.LayoutParams(-1,jarvisDp(64));
        menuCardLp2.bottomMargin=jarvisDp(7);
        jarvisDrawer.addView(write,menuCardLp2);
        LinearLayout.LayoutParams menuCardLp3=new LinearLayout.LayoutParams(-1,jarvisDp(64));
        menuCardLp3.bottomMargin=jarvisDp(7);
        jarvisDrawer.addView(settings,menuCardLp3);
        jarvisDrawer.addView(releaseNotes,new LinearLayout.LayoutParams(-1,jarvisDp(64)));'''
    if old_menu not in s: raise SystemExit(name+': drawer menu marker missing')
    s=s.replace(old_menu,new_menu,1)

    s=s.replace('new android.widget.FrameLayout.LayoutParams(jarvisDp(238),jarvisDp(430),Gravity.RIGHT|Gravity.CENTER_VERTICAL)',
                'new android.widget.FrameLayout.LayoutParams(jarvisDp(238),jarvisDp(486),Gravity.RIGHT|Gravity.CENTER_VERTICAL)',1)

    s=s.replace('JARVIS 1.9.5  •  UI PHASE 8B','JARVIS 1.9.8  •  CONTEXT MEMORY',1)
    s=s.replace('JARVIS 1.9.5  •  build 117','JARVIS 1.9.8  •  build 120',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  1.9.7','JARVIS  •  ELITE INTERFACE  •  1.9.8',1)

    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="120" android:versionName="1.9.8"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 120',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.9.8'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 1.9.8 context memory + release notes patch applied')
