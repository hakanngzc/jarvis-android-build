from pathlib import Path
import sys,re
base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'
h=java/'HybridActivity.java'
s=h.read_text(encoding='utf-8')

# PHASE 1: theme only. Keep original Activity, original onCreate flow and original setContentView structure.
needle='        LinearLayout root=(LinearLayout)content.getChildAt(0);content.removeView(root);\n'
if needle not in s:
    raise SystemExit('root marker missing')
s=s.replace(needle, needle+
'''        getWindow().setStatusBarColor(0xff020913);
        getWindow().setNavigationBarColor(0xff020913);
        getWindow().getDecorView().setBackgroundColor(0xff020913);
        root.setBackgroundColor(0xff020913);
''',1)

old='        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.addView(root);setContentView(scroll);'
new='        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setBackgroundColor(0xff020913);scroll.addView(root);setContentView(scroll);'
if old not in s:
    raise SystemExit('scroll marker missing')
s=s.replace(old,new,1)

old='if(s.contains("v1.5.7"))t.setText("JARVIS 1.7.0 · ONE BREATH COMMAND");'
new='if(s.contains("v1.5.7")){t.setText("J A R V I S");t.setTextSize(30);t.setTextColor(0xffe7f7ff);t.setGravity(Gravity.CENTER);if(android.os.Build.VERSION.SDK_INT>=21)t.setLetterSpacing(0.16f);}'
if old not in s:
    raise SystemExit('title marker missing')
s=s.replace(old,new,1)

# PHASE 2: add only the central JARVIS core. No Activity swap and no new DEX layer.
core_code=r'''        int jarvisTitleIndex=0;
        for(int i=0;i<root.getChildCount();i++){
            View v=root.getChildAt(i);
            if(v instanceof TextView && "J A R V I S".equals(((TextView)v).getText().toString())){jarvisTitleIndex=i;break;}
        }
        try{
            java.io.InputStream jarvisCoreStream=getAssets().open("jarvis_core.webp");
            android.graphics.Bitmap jarvisCoreBitmap=android.graphics.BitmapFactory.decodeStream(jarvisCoreStream);
            jarvisCoreStream.close();
            if(jarvisCoreBitmap!=null){
                ImageView jarvisCoreView=new ImageView(this);
                jarvisCoreView.setImageBitmap(jarvisCoreBitmap);
                jarvisCoreView.setScaleType(ImageView.ScaleType.CENTER_INSIDE);
                jarvisCoreView.setAdjustViewBounds(true);
                int jarvisCoreSize=(int)(260*getResources().getDisplayMetrics().density+0.5f);
                LinearLayout.LayoutParams jarvisCoreLp=new LinearLayout.LayoutParams(jarvisCoreSize,jarvisCoreSize);
                jarvisCoreLp.gravity=Gravity.CENTER_HORIZONTAL;
                jarvisCoreLp.topMargin=(int)(10*getResources().getDisplayMetrics().density+0.5f);
                jarvisCoreLp.bottomMargin=(int)(14*getResources().getDisplayMetrics().density+0.5f);
                root.addView(jarvisCoreView,Math.min(jarvisTitleIndex+1,root.getChildCount()),jarvisCoreLp);
            }
        }catch(Exception ignored){}
'''
anchor='        LinearLayout row=new LinearLayout(this);row.setOrientation(LinearLayout.HORIZONTAL);'
if anchor not in s:
    raise SystemExit('phase2 anchor missing')
s=s.replace(anchor,core_code+anchor,1)

# Persist the themed HybridActivity source before compiling/cloning it.
h.write_text(s,encoding='utf-8')

# Preserve the phone-confirmed 1.7.6 media-safe wake behavior exactly at source level.
o=java/'OpenWakeWordDetector.java';x=o.read_text(encoding='utf-8')
old='try{if(melSession==null)initModels();initBuffers();if(!initAudioRecord())throw new IllegalStateException("Mikrofon açılamadı");audioLoop();}'
new='try{if(!initAudioRecord())throw new IllegalStateException("Mikrofon açılamadı");if(melSession==null)initModels();initBuffers();audioLoop();}'
if old not in x: raise SystemExit('wake start marker missing')
x=x.replace(old,new,1)
old='registerRecordingDiagnostics(candidate);return true;'
new='candidate.startRecording();return true;'
if old not in x: raise SystemExit('audio start marker missing')
x=x.replace(old,new,1)
old='private void audioLoop(){AudioRecord r=audioRecord;if(r==null)return;r.startRecording();JarvisForensics.event(context,"A","startRecording state="+r.getRecordingState()+" source="+activeSource);'
new='private void audioLoop(){AudioRecord r=audioRecord;if(r==null)return;JarvisForensics.event(context,"A","startRecording state="+r.getRecordingState()+" source="+activeSource);'
if old not in x: raise SystemExit('audioLoop marker missing')
x=x.replace(old,new,1)
x=x.replace('if(score>=0.48f){','if(score>=0.42f){',1)
o.write_text(x,encoding='utf-8')

w=java/'WakeWordService.java';x=w.read_text(encoding='utf-8')
old='new OpenWakeWordDetector(this,0.30f,0.48f,3800L)'
new='new OpenWakeWordDetector(this,0.15f,0.42f,3800L)'
if old not in x: raise SystemExit('wake threshold marker missing')
x=x.replace(old,new,1)
w.write_text(x,encoding='utf-8')

# Version and launcher icon only. Launcher Activity remains HybridActivity.
m=base/'app/src/main/AndroidManifest.xml';x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="107" android:versionName="1.8.5"',x,count=1)
if 'android:icon="@drawable/jarvis_icon"' not in x:
    x=x.replace('<application android:label="JARVIS"','<application android:label="JARVIS" android:icon="@drawable/jarvis_icon" android:roundIcon="@drawable/jarvis_icon"',1)
if 'com.hakan.jarvis.DesignActivity' in x:
    raise SystemExit('unsafe DesignActivity found')
m.write_text(x,encoding='utf-8')

b=base/'app/build.gradle';g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 107',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.8.5'",g,count=1)
b.write_text(g,encoding='utf-8')


# Safe visible UI clone. The legacy HybridActivity remains in the baseline DEX, while this unique class carries the same engine plus the new UI.
home=java/'JarvisHomeActivity.java'
home_src=h.read_text(encoding='utf-8')
home_src=home_src.replace('HybridActivity','JarvisHomeActivity')
home.write_text(home_src,encoding='utf-8')

# Route every wake/direct handoff to the visible cloned home activity.
ws=java/'WakeWordService.java'
wx=ws.read_text(encoding='utf-8').replace('new Intent(this,HybridActivity.class)','new Intent(this,JarvisHomeActivity.class)')
ws.write_text(wx,encoding='utf-8')

# Launcher points at JarvisHomeActivity. The old HybridActivity bytecode remains untouched as a fallback engine class.
m=base/'app/src/main/AndroidManifest.xml'
mx=m.read_text(encoding='utf-8')
mx=mx.replace('android:name="com.hakan.jarvis.HybridActivity"','android:name="com.hakan.jarvis.JarvisHomeActivity"',1)
m.write_text(mx,encoding='utf-8')

print('JARVIS 1.8.5 UI PHASE 2 cloned home applied')

