from pathlib import Path
import sys,re
base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')
    owner='HybridActivity' if name=='HybridActivity.java' else 'JarvisHomeActivity'

    marker='''            boolean jarvisMediaNeedsApp=jarvisMediaCommand.action.equals("PLAY")
                ||jarvisMediaCommand.action.equals("SEARCH")
                ||jarvisMediaCommand.action.equals("OPEN");

            if(jarvisMediaNeedsApp&&!MediaActions.providerInstalled(this,jarvisMediaCommand.provider)){'''
    insert=f'''            boolean jarvisMediaNeedsApp=jarvisMediaCommand.action.equals("PLAY")
                ||jarvisMediaCommand.action.equals("SEARCH")
                ||jarvisMediaCommand.action.equals("OPEN");

            if(MediaActions.isTransportAction(jarvisMediaCommand)&&!MediaActions.hasSessionAccess(this)){{
                String needAccess="Medya kontrolü için Bildirim erişiminden JARVIS'e izin vermeniz gerekiyor efendim. Ayarları açıyorum.";
                if(answer!=null)answer.setText(needAccess);
                if(meta!=null)meta.setText("MediaSession Control · izin gerekli · Spotify/YouTube aktif oturumu");
                if(jarvisReadyLine!=null)jarvisReadyLine.setText("Medya kontrol erişimi gerekli.");
                if(jarvisAtomCore!=null)jarvisAtomCore.setMode(2);
                if(voice!=null)voice.beginTurn();
                say(needAccess,"",new Runnable(){{public void run(){{
                    try{{MediaActions.requestSessionAccess({owner}.this);}}catch(Exception ignored){{}}
                    if(jarvisAtomCore!=null)jarvisAtomCore.setMode(0);
                    if(jarvisReadyLine!=null)jarvisReadyLine.setText("Hazırım.");
                    WakeWordService.resume({owner}.this,"media_session_permission");
                }}}});
                return;
            }}

            if(jarvisMediaNeedsApp&&!MediaActions.providerInstalled(this,jarvisMediaCommand.provider)){{'''
    if marker not in s: raise SystemExit(name+': media permission insertion marker missing')
    s=s.replace(marker,insert,1)

    release='''        View n2021=jarvisReleaseCard("JARVIS 2.0.2.1","MEDIA PAUSE HOTFIX",'''
    newrelease='''        View n2022=jarvisReleaseCard("JARVIS 2.0.2.2","DIRECT MEDIASESSION CONTROL",
            "• AudioManager medya tuşu yerine Spotify/YouTube aktif MediaSession'ına doğrudan kontrol desteği eklendi.\\n• Pause, play, sonraki ve önceki komutları MediaController TransportControls üzerinden gönderilir.\\n• Bunun için Android Bildirim erişimi bir kez kullanıcı tarafından açılmalıdır.\\n• Erişim yoksa JARVIS işlem yapılmış gibi konuşmaz; izin ekranını açar.\\n• MediaSession bulunamazsa eski medya tuşu yöntemi yedek olarak korunur.",true);
        View n2021=jarvisReleaseCard("JARVIS 2.0.2.1","MEDIA PAUSE HOTFIX",'''
    if release not in s: raise SystemExit(name+': release 2021 marker missing')
    s=s.replace(release,newrelease,1)

    idx=s.find('View n2021=jarvisReleaseCard("JARVIS 2.0.2.1"')
    if idx<0: raise SystemExit(name+': n2021 missing')
    end=s.find('",true);',idx)
    if end>=0:
        s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': cards marker missing')
    s=s.replace(cards,'View[] cards={n2022,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2021";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2022";',1)
    s=s.replace('JARVIS 2.0.2.1  •  MEDIA HOTFIX','JARVIS 2.0.2.2  •  MEDIASESSION CONTROL',1)
    s=s.replace('JARVIS 2.0.2.1  •  build 125','JARVIS 2.0.2.2  •  build 126',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.2.1','JARVIS  •  ELITE INTERFACE  •  2.0.2.2',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
service='''        <service
            android:name=".JarvisMediaListener"
            android:label="JARVIS Medya Kontrolü"
            android:exported="false"
            android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">
            <intent-filter>
                <action android:name="android.service.notification.NotificationListenerService" />
            </intent-filter>
        </service>
'''
if 'android:name=".JarvisMediaListener"' not in x:
    if '</application>' not in x: raise SystemExit('manifest application marker missing')
    x=x.replace('</application>',service+'    </application>',1)
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="126" android:versionName="2.0.2.2"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 126',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.2.2'",g,count=1)
b.write_text(g,encoding='utf-8')
print('JARVIS 2.0.2.2 direct MediaSession control patch applied')
