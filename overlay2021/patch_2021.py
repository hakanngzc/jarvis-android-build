from pathlib import Path
import sys,re
base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    marker='''        View n202=jarvisReleaseCard("JARVIS 2.0.2","MEDIA ENTITY 4.0",'''
    insert='''        View n2021=jarvisReleaseCard("JARVIS 2.0.2.1","MEDIA PAUSE HOTFIX",
            "• 'Şarkıyı durdurur musun?', 'müziği durdurabilir misin?' ve 'duraklatır mısın?' gibi doğal Türkçe durdurma kalıpları eklendi.\\n• JARVIS müziği kendisi başlatmamış olsa bile aktif medya oturumuna PAUSE komutu gönderebilir.\\n• Spotify adı açıkça söylenirse Spotify bağlamı korunur.\\n• Önce sesli geri dönüş, ardından medya işlemi sırası korunur.",true);
        View n202=jarvisReleaseCard("JARVIS 2.0.2","MEDIA ENTITY 4.0",'''
    if marker not in s: raise SystemExit(name+': release 202 marker missing')
    s=s.replace(marker,insert,1)

    idx=s.find('View n202=jarvisReleaseCard("JARVIS 2.0.2"')
    if idx<0: raise SystemExit(name+': n202 not found after insert')
    end=s.find('",true);',idx)
    if end<0: raise SystemExit(name+': n202 current marker missing')
    s=s[:end]+ '",false);' + s[end+8:]

    cards='View[] cards={n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s: raise SystemExit(name+': cards marker missing')
    s=s.replace(cards,'View[] cards={n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_202";',
                'private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2021";',1)

    s=s.replace('JARVIS 2.0.2  •  MEDIA ENTITY 4.0','JARVIS 2.0.2.1  •  MEDIA HOTFIX',1)
    s=s.replace('JARVIS 2.0.2  •  build 124','JARVIS 2.0.2.1  •  build 125',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.2','JARVIS  •  ELITE INTERFACE  •  2.0.2.1',1)

    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="125" android:versionName="2.0.2.1"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 125',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.2.1'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.2.1 media pause hotfix applied')
