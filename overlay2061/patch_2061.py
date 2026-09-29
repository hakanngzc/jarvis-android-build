from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')
    owner='HybridActivity' if name=='HybridActivity.java' else 'JarvisHomeActivity'

    marker='''        if(jarvisContactFlow.length()==0 && jarvisBrain.rewritten && !jarvisBrain.protectedFreeText){
            raw=jarvisBrain.routedCommand;
        }
'''
    insert=f'''        if(jarvisContactFlow.length()==0 && jarvisBrain.rewritten && !jarvisBrain.protectedFreeText){{
            raw=jarvisBrain.routedCommand;
        }}

        final SystemAlarmBridge.Plan jarvisSystemAlarm=SystemAlarmBridge.parse(raw,System.currentTimeMillis());
        if(jarvisSystemAlarm!=null){{
            final String alarmReply=\"Saat \"+jarvisSystemAlarm.timeText()+\" için sistem alarmını kuruyorum efendim.\";
            if(answer!=null)answer.setText(alarmReply);
            if(meta!=null)meta.setText(\"System Clock Alarm · \"+jarvisSystemAlarm.timeText()+\" · izin penceresi yok\");
            if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText(\"Cevap: \"+alarmReply);
            if(jarvisAnswerLine!=null)jarvisAnswerLine.setText(\"Cevap: \"+alarmReply);
            if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText(\"JARVIS  •  \"+alarmReply);
            if(jarvisReadyLine!=null)jarvisReadyLine.setText(\"Sistem Saat alarmı hazırlanıyor...\");
            if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
            if(voice!=null)voice.beginTurn();

            say(alarmReply,\"\",new Runnable(){{public void run(){{
                SystemAlarmBridge.Result result=SystemAlarmBridge.setAlarm({owner}.this,jarvisSystemAlarm);
                if(result.success){{
                    if(meta!=null)meta.setText(\"System Clock Alarm · aktif · \"+jarvisSystemAlarm.timeText());
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText(\"Hazırım.\");
                    if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                    WakeWordService.resume({owner}.this,\"system_clock_alarm_done\");
                    return;
                }}

                final String fail=\"Sistem Saat uygulamasına alarmı aktaramadım efendim.\";
                if(answer!=null)answer.setText(fail);
                if(meta!=null)meta.setText(\"System Clock Alarm · başarısız · \"+result.note);
                if(jarvisOverlayAnswerLine!=null)jarvisOverlayAnswerLine.setText(\"Cevap: \"+fail);
                if(jarvisAnswerLine!=null)jarvisAnswerLine.setText(\"Cevap: \"+fail);
                if(jarvisWriteAnswerLine!=null)jarvisWriteAnswerLine.setText(\"JARVIS  •  \"+fail);
                say(fail,\"\",new Runnable(){{public void run(){{
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText(\"Hazırım.\");
                    if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                    WakeWordService.resume({owner}.this,\"system_clock_alarm_failed\");
                }}}});
            }}}});
            return;
        }}
'''
    if marker not in s:
        raise SystemExit(name+': Brain dispatch marker missing')
    s=s.replace(marker,insert,1)

    s=s.replace('        AlarmStore.restore(this);\n','')

    old_settings='layout.addView(button("ALARMLARIM",new View.OnClickListener(){public void onClick(View v){showAlarms();}}));'
    new_settings='layout.addView(button("ALARMLARIM",new View.OnClickListener(){public void onClick(View v){SystemAlarmBridge.showAlarms('+owner+'.this);}}));'
    if old_settings in s:
        s=s.replace(old_settings,new_settings,1)

    known='''        boolean known=pc!=null
            ||jarvisContactFlow.length()>0
            ||jarvisSemanticPending!=null'''
    known_new='''        boolean known=pc!=null
            ||SystemAlarmBridge.parse(top,System.currentTimeMillis())!=null
            ||jarvisContactFlow.length()>0
            ||jarvisSemanticPending!=null'''
    if known not in s:
        raise SystemExit(name+': known marker missing')
    s=s.replace(known,known_new,1)

    profile='''    private static final String JARVIS_INTELLIGENCE_PROFILE="INTELLIGENCE_CORE_STAGE1_V1";
    private static final String JARVIS_BRAIN_PROFILE="BRAIN_ENGINE_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_206";'''
    profile_new='''    private static final String JARVIS_INTELLIGENCE_PROFILE="INTELLIGENCE_CORE_STAGE1_V1";
    private static final String JARVIS_BRAIN_PROFILE="BRAIN_ENGINE_V1";
    private static final String JARVIS_SYSTEM_ALARM_PROFILE="SYSTEM_CLOCK_ALARM_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2061";'''
    if profile not in s:
        raise SystemExit(name+': 2.0.6 profile marker missing')
    s=s.replace(profile,profile_new,1)

    release='''        View n206=jarvisReleaseCard("JARVIS 2.0.6","BRAIN ENGINE 1.0",'''
    if release not in s:
        raise SystemExit(name+': 2.0.6 release marker missing')
    s=s.replace(release,
'''        View n2061=jarvisReleaseCard("JARVIS 2.0.6.1","SYSTEM CLOCK ALARM",
            "• Alarm kurma JARVIS'in kendi AlarmManager/AlarmStore hattından sistem Saat uygulamasına taşındı.\\n• ACTION_SET_ALARM + EXTRA_SKIP_UI kullanılır; destekleyen Saat uygulaması alarmı ara ekran göstermeden etkinleştirir.\\n• SET_ALARM normal manifest iznidir; runtime izin penceresi açılmaz.\\n• SCHEDULE_EXACT_ALARM ve USE_EXACT_ALARM manifestten kaldırılır; Vivo exact-alarm izin akışına ihtiyaç kalmaz.\\n• JARVIS önce sesli geri dönüş verir, ardından alarmı sistem Saat uygulamasına yollar.\\n• '20 dakika sonra', 'yarım saat sonra', '2 saat sonra', 'saat 7', '07:30', 'akşam 8' gibi alarm biçimleri desteklenir.\\n• Ayarlar > Alarmlarım artık JARVIS iç alarm listesini değil sistem Saat alarm sayfasını açar.\\n• Brain Engine 1.0 ve tüm 2.0.6 özellikleri korunur.",true);
        View n206=jarvisReleaseCard("JARVIS 2.0.6","BRAIN ENGINE 1.0",''',1)

    idx=s.find('View n206=jarvisReleaseCard("JARVIS 2.0.6"')
    end=s.find('",true);',idx)
    if idx<0 or end<0:
        raise SystemExit(name+': current 2.0.6 card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n206,n2055,n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s:
        raise SystemExit(name+': release cards marker missing')
    s=s.replace(cards,'View[] cards={n2061,n206,n2055,n2054,n2053,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 2.0.6  •  BRAIN ENGINE 1.0','JARVIS 2.0.6.1  •  SYSTEM CLOCK ALARM',1)
    s=s.replace('JARVIS 2.0.6  •  build 137','JARVIS 2.0.6.1  •  build 138',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.6','JARVIS  •  ELITE INTERFACE  •  2.0.6.1',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'\s*<uses-permission android:name="android\.permission\.SCHEDULE_EXACT_ALARM"\s*/>','',x)
x=re.sub(r'\s*<uses-permission android:name="android\.permission\.USE_EXACT_ALARM"\s*/>','',x)
if 'com.android.alarm.permission.SET_ALARM' not in x:
    pos=x.find('<application')
    x=x[:pos]+'  <uses-permission android:name="com.android.alarm.permission.SET_ALARM" />\n'+x[pos:]
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="138" android:versionName="2.0.6.1"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 138',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.6.1'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.6.1 System Clock Alarm patch applied')
