from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')
    owner='HybridActivity' if name=='HybridActivity.java' else 'JarvisHomeActivity'

    field='''    private String jarvisLastAppTarget="";
    private long jarvisLastAppAt=0L;
'''
    newfield='''    private String jarvisLastAppTarget="";
    private long jarvisLastAppAt=0L;
    private String jarvisLastContactTarget="";
    private long jarvisLastContactAt=0L;
    private String jarvisContactFlow="";
    private ContactCommandRouter.Command jarvisPendingContactCommand=null;
    private ContactActions.ResolvedContact jarvisPendingResolvedContact=null;
'''
    if field not in s: raise SystemExit(name+': contact field marker missing')
    s=s.replace(field,newfield,1)

    dispatch='''    private void dispatch(String raw){
        String jarvisOriginalRaw=raw;
'''
    helpers=f'''    private void jarvisContactUi(String text,String detail){{
        if(answer!=null)answer.setText(text);
        if(meta!=null)meta.setText(detail==null?"Contact Intelligence 1.0":detail);
        if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText("Cevap: "+text);
        if(jarvisAnswerLine!=null)jarvisAnswerLine.setText("Cevap: "+text);
        if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText("JARVIS  •  "+text);
        if(jarvisReadyLine!=null)jarvisReadyLine.setText("Yanıtlıyorum...");
        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
    }}

    private void jarvisContactEnd(String reason){{
        if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
        if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
        WakeWordService.resume(this,reason);
    }}

    private void jarvisContactSpeak(final String text,final String detail,final Runnable after){{
        jarvisContactUi(text,detail);
        if(voice!=null)voice.beginTurn();
        say(text,"",new Runnable(){{public void run(){{
            if(after!=null)after.run();
        }}}});
    }}

    private void jarvisClearContactPending(){{
        jarvisContactFlow="";
        jarvisPendingContactCommand=null;
        jarvisPendingResolvedContact=null;
    }}

    private String jarvisChannelName(String channel){{
        return "whatsapp".equals(channel)?"WhatsApp":"mesaj";
    }}

    private String jarvisContactConfirmText(ContactActions.ResolvedContact c,ContactCommandRouter.Command cmd){{
        String msg=cmd==null?"":cmd.message;
        String preview=msg.length()>110?msg.substring(0,110)+"…":msg;
        return c.displayName+" kişisine "+jarvisChannelName(cmd.channel)+" üzerinden “"+preview+"” yazmamı onaylıyor musunuz?";
    }}

''' + dispatch
    if dispatch not in s: raise SystemExit(name+': dispatch marker missing')
    s=s.replace(dispatch,helpers,1)

    marker='''        final DeviceCommandRouter.Command jarvisDeviceCommand=DeviceCommandRouter.parse(raw);'''
    contact_block=f'''        if("WAIT_MESSAGE".equals(jarvisContactFlow)&&jarvisPendingContactCommand!=null&&jarvisPendingResolvedContact!=null){{
            if(ContactCommandRouter.no(raw)){{
                jarvisClearContactPending();
                jarvisContactSpeak("Mesajı iptal ettim efendim.","Contact Intelligence 1.0 · mesaj iptal",new Runnable(){{public void run(){{jarvisContactEnd("contact_message_cancel");}}}});
                return;
            }}
            String body=ContactCommandRouter.stripWake(raw).trim();
            if(body.length()==0){{
                jarvisContactSpeak("Mesaj metnini anlayamadım efendim. Ne yazmamı istediğinizi tekrar söyleyin.","Contact Intelligence 1.0 · mesaj metni bekleniyor",new Runnable(){{public void run(){{jarvisContactEnd("contact_wait_message");}}}});
                return;
            }}
            jarvisPendingContactCommand=jarvisPendingContactCommand.withMessage(body);
            jarvisContactFlow="WAIT_CONFIRM";
            final String confirm=jarvisContactConfirmText(jarvisPendingResolvedContact,jarvisPendingContactCommand);
            jarvisContactSpeak(confirm,"Contact Intelligence 1.0 · gönderim onayı",new Runnable(){{public void run(){{jarvisContactEnd("contact_wait_confirm");}}}});
            return;
        }}

        if("WAIT_CONFIRM".equals(jarvisContactFlow)&&jarvisPendingContactCommand!=null&&jarvisPendingResolvedContact!=null){{
            if(ContactCommandRouter.yes(raw)){{
                final ContactCommandRouter.Command cmd=jarvisPendingContactCommand;
                final ContactActions.ResolvedContact contact=jarvisPendingResolvedContact;
                jarvisClearContactPending();
                final String reply="Onaylandı efendim. "+contact.displayName+" için "+jarvisChannelName(cmd.channel)+" mesajını hazırlıyorum.";
                jarvisContactSpeak(reply,"Contact Intelligence 1.0 · onaylandı",new Runnable(){{public void run(){{
                    ContactActions.ActionResult result;
                    if("whatsapp".equals(cmd.channel))result=ContactActions.composeWhatsApp({owner}.this,contact,cmd.message);
                    else result=ContactActions.composeSms({owner}.this,contact,cmd.message);
                    jarvisLastContactTarget=contact.displayName;
                    jarvisLastContactAt=android.os.SystemClock.elapsedRealtime();
                    if(!result.success){{
                        final String fail="Mesaj taslağını açamadım efendim.";
                        jarvisContactSpeak(fail,"Contact Intelligence 1.0 · mesaj açılamadı · "+result.note,new Runnable(){{public void run(){{jarvisContactEnd("contact_message_failed");}}}});
                        return;
                    }}
                    jarvisContactEnd("contact_message_ready");
                }}}});
                return;
            }}
            if(ContactCommandRouter.no(raw)){{
                jarvisClearContactPending();
                jarvisContactSpeak("Gönderimi iptal ettim efendim.","Contact Intelligence 1.0 · onay reddedildi",new Runnable(){{public void run(){{jarvisContactEnd("contact_confirm_cancel");}}}});
                return;
            }}
            jarvisContactSpeak("Onay için evet, iptal etmek için hayır deyin efendim.","Contact Intelligence 1.0 · onay bekleniyor",new Runnable(){{public void run(){{jarvisContactEnd("contact_wait_confirm");}}}});
            return;
        }}

        long jarvisContactAge=jarvisLastContactAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisLastContactAt);
        final ContactCommandRouter.Command jarvisContactCommand=ContactCommandRouter.parse(raw,jarvisLastContactTarget,jarvisContactAge);
        if(jarvisContactCommand!=null){{
            onlineConversationTopic="";
            onlineConversationTopicAt=0L;
            jarvisLastActionCommand="";
            jarvisLastActionAt=0L;

            if(!ContactActions.hasContactsPermission(this)){{
                final String need="Rehberdeki kişileri anlayabilmem için kişi erişim izni gerekiyor efendim. İzin ekranını açıyorum.";
                jarvisContactSpeak(need,"Contact Intelligence 1.0 · READ_CONTACTS gerekli",new Runnable(){{public void run(){{
                    try{{ContactActions.requestContactsPermission({owner}.this);}}catch(Exception ignored){{}}
                    jarvisContactEnd("contact_permission");
                }}}});
                return;
            }}

            final ContactActions.ResolveResult rr=ContactActions.resolve(this,jarvisContactCommand.target);
            if("AMBIGUOUS".equals(rr.status)){{
                final String msg="Birden fazla benzer kişi buldum efendim: "+rr.candidates+". Tam adıyla tekrar söyleyin.";
                jarvisContactSpeak(msg,"Contact Intelligence 1.0 · belirsiz kişi",new Runnable(){{public void run(){{jarvisContactEnd("contact_ambiguous");}}}});
                return;
            }}
            if(!"FOUND".equals(rr.status)||rr.contact==null){{
                final String msg=jarvisContactCommand.target+" için rehberde güvenilir bir eşleşme bulamadım efendim.";
                jarvisContactSpeak(msg,"Contact Intelligence 1.0 · kişi bulunamadı",new Runnable(){{public void run(){{jarvisContactEnd("contact_not_found");}}}});
                return;
            }}

            final ContactActions.ResolvedContact contact=rr.contact;
            jarvisLastContactTarget=contact.displayName;
            jarvisLastContactAt=android.os.SystemClock.elapsedRealtime();

            if("CALL".equals(jarvisContactCommand.action)){{
                final boolean direct=ContactActions.canDirectCall(this);
                final String reply=direct
                    ?contact.displayName+" kişisini arıyorum efendim."
                    :"Arama izni doğrudan aramaya izin vermiyor efendim. "+contact.displayName+" numarasını çeviricide açıyorum.";
                jarvisContactSpeak(reply,"Contact Intelligence 1.0 · CALL · "+contact.displayName,new Runnable(){{public void run(){{
                    ContactActions.ActionResult result=ContactActions.call({owner}.this,contact);
                    if(!result.success){{
                        jarvisContactSpeak("Arama ekranını açamadım efendim.","Contact Intelligence 1.0 · arama başarısız · "+result.note,new Runnable(){{public void run(){{jarvisContactEnd("contact_call_failed");}}}});
                        return;
                    }}
                    jarvisContactEnd("contact_call_done");
                }}}});
                return;
            }}

            if("MESSAGE".equals(jarvisContactCommand.action)){{
                jarvisPendingResolvedContact=contact;
                jarvisPendingContactCommand=jarvisContactCommand;

                if(jarvisContactCommand.message.length()==0){{
                    jarvisContactFlow="WAIT_MESSAGE";
                    final String ask=contact.displayName+" kişisine "+jarvisChannelName(jarvisContactCommand.channel)+" üzerinden ne yazmamı istersiniz?";
                    jarvisContactSpeak(ask,"Contact Intelligence 1.0 · mesaj metni bekleniyor",new Runnable(){{public void run(){{jarvisContactEnd("contact_wait_message");}}}});
                    return;
                }}

                jarvisContactFlow="WAIT_CONFIRM";
                final String confirm=jarvisContactConfirmText(contact,jarvisContactCommand);
                jarvisContactSpeak(confirm,"Contact Intelligence 1.0 · gönderim onayı",new Runnable(){{public void run(){{jarvisContactEnd("contact_wait_confirm");}}}});
                return;
            }}
        }}

        final DeviceCommandRouter.Command jarvisDeviceCommand=DeviceCommandRouter.parse(raw);'''
    if marker not in s: raise SystemExit(name+': device router marker missing')
    s=s.replace(marker,contact_block,1)

    known='''        long appKnownAge=jarvisLastAppAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisLastAppAt);
        boolean known=pc!=null
            ||DeviceCommandRouter.parse(top)!=null'''
    known_new='''        long appKnownAge=jarvisLastAppAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisLastAppAt);
        long contactKnownAge=jarvisLastContactAt<=0L?Long.MAX_VALUE:(android.os.SystemClock.elapsedRealtime()-jarvisLastContactAt);
        boolean known=pc!=null
            ||jarvisContactFlow.length()>0
            ||ContactCommandRouter.parse(top,jarvisLastContactTarget,contactKnownAge)!=null
            ||DeviceCommandRouter.parse(top)!=null'''
    if known not in s: raise SystemExit(name+': known-intent marker missing')
    s=s.replace(known,known_new,1)

    release='''        View n204=jarvisReleaseCard("JARVIS 2.0.4","APP CONTROL + NATURAL MEDIA",'''
    newrelease='''        View n205=jarvisReleaseCard("JARVIS 2.0.5","CONTACT INTELLIGENCE + MESSAGING",
            "• Rehber isimleri ve Android kişi kartındaki nickname/takma ad alanları birlikte eşleştirilir.\\n• 'Ahmet'i ara', 'Biraderimi ara' gibi ekli Türkçe kişi komutları için güvenli varyant eşleştirmesi eklendi.\\n• İki kişi benzer eşleşirse JARVIS rastgele seçim yapmaz; tam isim ister.\\n• 'İkbal'e WhatsApp'tan merhaba yaz', 'Ahmet'e mesaj gönder' ve bağlamsal 'olmadı WhatsApp'tan yaz' komutları eklendi.\\n• Mesaj metni eksikse JARVIS ne yazacağını sorar; ardından gönderim öncesi evet/hayır onayı ister.\\n• SMS Android ACTION_SENDTO ile, WhatsApp resmi Click to Chat bağlantısıyla taslak olarak açılır; JARVIS kullanıcı adına arka planda otomatik gönderim yapmaz.\\n• Son kişi 5 dakika tutulur; 'onu ara', 'ona mesaj at', 'WhatsApp'tan yaz' gibi kısa devam komutları çalışır.\\n• App Control, Natural Media, Device Control, Spotify OAuth, alarm, wake word ve hibrit çekirdek korunur.",true);
        View n204=jarvisReleaseCard("JARVIS 2.0.4","APP CONTROL + NATURAL MEDIA",'''
    if release not in s: raise SystemExit(name+': 2.0.4 release marker missing')
    s=s.replace(release,newrelease,1)

    idx=s.find('View n204=jarvisReleaseCard("JARVIS 2.0.4"')
    end=s.find('",true);',idx)
    if idx<0 or end<0: raise SystemExit(name+': current 2.0.4 card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': release card list marker missing')
    s=s.replace(cards,'View[] cards={n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_204";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_205";',1)
    s=s.replace('JARVIS 2.0.4  •  APP + MEDIA CONTEXT','JARVIS 2.0.5  •  CONTACT INTELLIGENCE',1)
    s=s.replace('JARVIS 2.0.4  •  build 130','JARVIS 2.0.5  •  build 131',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.4','JARVIS  •  ELITE INTERFACE  •  2.0.5',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
for permission in [
    '<uses-permission android:name="android.permission.READ_CONTACTS" />',
    '<uses-permission android:name="android.permission.CALL_PHONE" />'
]:
    if permission not in x:
        pos=x.find('<application')
        if pos<0: raise SystemExit('manifest application marker missing')
        x=x[:pos]+permission+'\n    '+x[pos:]

x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="131" android:versionName="2.0.5"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 131',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.5'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.5 Contact Intelligence + Messaging patch applied')
