from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    marker='''        View n2022=jarvisReleaseCard("JARVIS 2.0.2.3","EXACT SONG RESOLVER",'''
    insert='''        View n2024=jarvisReleaseCard("JARVIS 2.0.2.4","SPOTIFY OAUTH + EXACT TRACK URI",
            "• Spotify Authorization Code + PKCE OAuth eklendi; client secret APK içine gömülmez.\\n• Redirect URI: http://127.0.0.1:43821/callback.\\n• Access ve refresh token Android Keystore ile AES-GCM şifrelenerek saklanır.\\n• Spotify /v1/search ile gerçek track URI seçilir, /v1/me/player/play ile doğrudan o parça oynatılır.\\n• Pause, resume, next ve previous komutları mümkün olduğunda Spotify Web API üzerinden gider.\\n• Aktif Spotify Connect cihazı yoksa uygulama gerçek track URI ile açılır ve MediaSession fallback korunur.\\n• İlk kullanımda Spotify hesabı bir kez bağlanır; token süresi dolunca refresh token otomatik yenilenir.",true);
        View n2022=jarvisReleaseCard("JARVIS 2.0.2.3","EXACT SONG RESOLVER",'''
    if marker not in s: raise SystemExit(name+': 2.0.2.3 release marker missing')
    s=s.replace(marker,insert,1)

    idx=s.find('View n2022=jarvisReleaseCard("JARVIS 2.0.2.3"')
    end=s.find('",true);',idx)
    if idx<0 or end<0: raise SystemExit(name+': current 2.0.2.3 marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': release cards marker missing')
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

print('JARVIS 2.0.2.4 Spotify OAuth + Exact Track URI patch applied')
