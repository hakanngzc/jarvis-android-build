from pathlib import Path
import sys,re

base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'

LIVE=r'''        LinearLayout liveStrip=new LinearLayout(this);
        liveStrip.setOrientation(LinearLayout.VERTICAL);
        liveStrip.setGravity(Gravity.CENTER_VERTICAL);
        liveStrip.setClipChildren(true);
        liveStrip.setClipToPadding(true);
        liveStrip.setPadding(jarvisDp(14),0,jarvisDp(14),0);
        liveStrip.setBackground(jarvisBg(0x8f06131f,0xff164f73,18));

        jarvisOverlayCommandLine=jarvisText("Komut: —",13,0xffdceef9);
        jarvisOverlayCommandLine.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        jarvisOverlayCommandLine.setSingleLine(true);
        jarvisOverlayCommandLine.setLines(1);
        jarvisOverlayCommandLine.setMinLines(1);
        jarvisOverlayCommandLine.setMaxLines(1);
        jarvisOverlayCommandLine.setMinHeight(jarvisDp(27));
        jarvisOverlayCommandLine.setMaxHeight(jarvisDp(27));
        jarvisOverlayCommandLine.setHeight(jarvisDp(27));
        jarvisOverlayCommandLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        jarvisOverlayCommandLine.setHorizontallyScrolling(false);
        jarvisOverlayCommandLine.setPadding(0,0,0,0);
        if(android.os.Build.VERSION.SDK_INT>=17){
            jarvisOverlayCommandLine.setTextDirection(View.TEXT_DIRECTION_LTR);
            jarvisOverlayCommandLine.setTextAlignment(View.TEXT_ALIGNMENT_VIEW_START);
        }
        liveStrip.addView(jarvisOverlayCommandLine,new LinearLayout.LayoutParams(-1,jarvisDp(27)));

        View liveDivider=new View(this);
        liveDivider.setBackgroundColor(0x331b7fb3);
        LinearLayout.LayoutParams dividerLp=new LinearLayout.LayoutParams(-1,jarvisDp(1));
        liveStrip.addView(liveDivider,dividerLp);

        jarvisOverlayAnswerLine=jarvisText("Cevap: —",13,0xff7fcfff);
        jarvisOverlayAnswerLine.setGravity(Gravity.LEFT|Gravity.CENTER_VERTICAL);
        jarvisOverlayAnswerLine.setSingleLine(true);
        jarvisOverlayAnswerLine.setLines(1);
        jarvisOverlayAnswerLine.setMinLines(1);
        jarvisOverlayAnswerLine.setMaxLines(1);
        jarvisOverlayAnswerLine.setMinHeight(jarvisDp(27));
        jarvisOverlayAnswerLine.setMaxHeight(jarvisDp(27));
        jarvisOverlayAnswerLine.setHeight(jarvisDp(27));
        jarvisOverlayAnswerLine.setEllipsize(android.text.TextUtils.TruncateAt.END);
        jarvisOverlayAnswerLine.setHorizontallyScrolling(false);
        jarvisOverlayAnswerLine.setPadding(0,0,0,0);
        if(android.os.Build.VERSION.SDK_INT>=17){
            jarvisOverlayAnswerLine.setTextDirection(View.TEXT_DIRECTION_LTR);
            jarvisOverlayAnswerLine.setTextAlignment(View.TEXT_ALIGNMENT_VIEW_START);
        }
        liveStrip.addView(jarvisOverlayAnswerLine,new LinearLayout.LayoutParams(-1,jarvisDp(27)));

        LinearLayout.LayoutParams liveStripLp=new LinearLayout.LayoutParams(-1,jarvisDp(64));
        liveStripLp.leftMargin=jarvisDp(10);
        liveStripLp.rightMargin=jarvisDp(10);
        liveStripLp.topMargin=jarvisDp(6);
        liveStripLp.bottomMargin=0;
        stack.addView(liveStrip,liveStripLp);
'''

for name in ['HybridActivity.java','JarvisHomeActivity.java']:
    p=java/name
    s=p.read_text(encoding='utf-8')

    if LIVE not in s:
        raise SystemExit(name+': command/answer strip marker missing')
    hidden_state=r'''        jarvisOverlayCommandLine=jarvisText("Komut: —",13,0xffdceef9);
        jarvisOverlayAnswerLine=jarvisText("Cevap: —",13,0xff7fcfff);
'''
    s=s.replace(LIVE,hidden_state,1)

    old_core='''        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(jarvisDp(292),jarvisDp(292));
        cp.bottomMargin=jarvisDp(6);stack.addView(atomStage,cp);'''
    new_core='''        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(jarvisDp(356),jarvisDp(356));
        cp.bottomMargin=jarvisDp(10);stack.addView(atomStage,cp);'''
    if old_core not in s:
        raise SystemExit(name+': core size marker missing')
    s=s.replace(old_core,new_core,1)

    profile='''    private static final String JARVIS_UI_COMMAND_STRIP_PROFILE="UI_COMMAND_STRIP_STABLE_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2051";'''
    new_profile='''    private static final String JARVIS_HOME_CORE_PROFILE="HOME_CORE_LARGE_DOUBLE_MOTION_CRASHFIX_V1";
    private static final String JARVIS_RELEASE_NOTES_PROFILE="RELEASE_NOTES_2053";'''
    if profile not in s:
        raise SystemExit(name+': 2.0.5.1 profile marker missing')
    s=s.replace(profile,new_profile,1)

    release='''        View n2051=jarvisReleaseCard("JARVIS 2.0.5.1","MAIN COMMAND STRIP STABILITY",'''
    if release not in s:
        raise SystemExit(name+': 2.0.5.1 release marker missing')
    s=s.replace(release,
'''        View n2052=jarvisReleaseCard("JARVIS 2.0.5.3","LARGE CORE + DOUBLE MOTION",
            "• Ana menüdeki Komut/Cevap paneli tamamen kaldırıldı.\\n• Çekirdek 292dp'den 356dp'ye büyütüldü ve boşalan alan çekirdeğe verildi.\\n• Çekirdeğin tam animasyon döngüsü 9000 ms'den 4500 ms'ye düşürüldü; orbit, pulse, elektron bulutu ve precession hareketleri gerçek 2× hızda çalışır.\\n• Ana ekran daha sade, çekirdek daha baskın hale getirildi.\\n• 2.0.5 Contact Intelligence ve tüm önceki motorlar korunur.",true);
        View n2051=jarvisReleaseCard("JARVIS 2.0.5.1","MAIN COMMAND STRIP STABILITY",''',1)

    idx=s.find('View n2051=jarvisReleaseCard("JARVIS 2.0.5.1"')
    end=s.find('",true);',idx)
    if idx<0 or end<0:
        raise SystemExit(name+': current 2.0.5.1 card marker missing')
    s=s[:end]+'",false);'+s[end+8:]

    cards='View[] cards={n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};'
    if cards not in s:
        raise SystemExit(name+': release cards marker missing')
    s=s.replace(cards,'View[] cards={n2053,n2052,n2051,n205,n204,n203,n2024,n2022,n2022legacy,n2021,n202,n201,n200,n199,n198,n197,n196,n195,n164};',1)

    s=s.replace('JARVIS 2.0.5.1  •  UI STABILITY','JARVIS 2.0.5.3  •  LARGE CORE',1)
    s=s.replace('JARVIS 2.0.5.1  •  build 132','JARVIS 2.0.5.3  •  build 133',1)
    s=s.replace('JARVIS  •  ELITE INTERFACE  •  2.0.5.1','JARVIS  •  ELITE INTERFACE  •  2.0.5.3',1)
    p.write_text(s,encoding='utf-8')

m=base/'app/src/main/AndroidManifest.xml'
x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"',
         'android:versionCode="134" android:versionName="2.0.5.3"',x,count=1)
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle'
g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 134',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '2.0.5.3'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 2.0.5.3 large core + double motion crashfix patch applied')
