from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    marker='''        View n2022=jarvisReleaseCard("JARVIS 2.0.2.3","EXACT SONG RESOLVER",'''
    insert='''        View n2024=jarvisReleaseCard("JARVIS 2.0.2.4","SPOTIFY WEB API OAUTH",
            "• Spotify Authorization Code + PKCE akışı eklendi; client secret APK içine gömülmez.\\n• İlk Spotify oynatma komutunda hesap yetkilendirmesi açılır ve access/refresh token cihazın özel uygulama alanında tutulur.\\n• Spotify Search API ile track + artist filtresi kullanılarak gerçek Spotify track URI seçilir.\\n• Seçilen spotify:track URI /me/player/play endpoint'ine gönderilir.\\n• 401 durumunda refresh token ile bir kez otomatik yenileme yapılır.\\n• API/hesap/aktif cihaz sorunu olursa Direct MediaSession sistemi fallback olarak korunur.\\n• Pause, resume, next ve previous Spotify OAuth bağlıyken Web API üzerinden gönderilir.",true);
        View n2022=jarvisReleaseCard("JARVIS 2.0.2.3","EXACT SONG RESOLVER",'''
    if marker not in s: raise SystemExit(name+': 2.0.2.3 release marker missing')
    s=s.replace(marker,insert,1)

    idx=s.find('View n2022=jarvisReleaseCard("JARVIS 2.0.2.3"')
    end=s.find('",true);',idx)
    if idx<0 or end<0: raise SystemExit(name+': n2022 current marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': cards marker missing')
    s=s.replace(cards,'View[] cards={n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2023";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2024";',1)
    s=s.replace('JARVIS 2.0.2.3  •  EXACT SONG RESOLVER','JARVIS 2.0.2.4  •  SPOTIFY OAUTH',1)
    s=s.replace('JARVIS 2.0.2.3  •  build 127','JARVIS 2.0.2.4  •  build 128',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.2.3','JARVIS  •  ELITE INTERFACE  •  2.0.2.4',1)

    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="128" android:versionName="2.0.2.4"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 128',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.2.4'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.2.4 Spotify Web API OAuth patch applied')
