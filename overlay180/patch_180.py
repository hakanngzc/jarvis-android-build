from pathlib import Path
import sys,re
base=Path(sys.argv[1])
java=base/'app/src/main/java/com/hakan/jarvis'
h=java/'HybridActivity.java'
s=h.read_text(encoding='utf-8')

# Fields used by the final home UI.
needle='    private Button retry,cancel;\n'
if needle in s and 'private LinearLayout jarvisDrawer;' not in s:
    s=s.replace(needle,needle+'    private LinearLayout jarvisDrawer;\n    private boolean jarvisDrawerOpen;\n',1)

# Replace onCreate completely, preserving engine initialization and 1.7.0 wake wiring.
start=s.index('    @Override protected void onCreate(Bundle state) {')
marker='    @Override protected void onNewIntent(Intent intent)'
# patch_170 inserts onNewIntent before button(); if absent use button marker.
end=s.find(marker,start)
if end<0:
    end=s.index('    private Button button(String title,View.OnClickListener action)',start)
new_oncreate=r'''    @Override protected void onCreate(Bundle state) {
        prefs=getSharedPreferences("jarvis_hybrid",MODE_PRIVATE);
        AlarmStore.restore(this);
        super.onCreate(state);
        http=new HybridEngine.HttpsTransport();engine=new HybridEngine(getFilesDir(),http);
        buildJarvisHomeUi();
        if(state!=null){
            answer.setText(state.getString("hybrid_answer",answer.getText().toString()));
            meta.setText(state.getString("hybrid_meta",""));
            String k=state.getString("last_kind");
            if(k!=null){last=new HybridEngine.Request(k,state.getString("last_query",""));retry.setVisibility(View.VISIBLE);}
        }
        updateHybridStatus();
        setVolumeControlStream(android.media.AudioManager.STREAM_MUSIC);
        voice=new VoiceController(this,new VoiceController.Listener(){public void state(String state,String detail){if(!dead&&voiceStatus!=null)voiceStatus.setText("Ses: "+state+(detail.length()>0?" · "+detail:""));}});
        phone=new PhoneActions(this,new PhoneActions.Host(){public void say(String text,String key,Runnable after){HybridActivity.this.say(text,key,after);}public void show(String title,String detail){setText(2002,title);setText(2003,detail.split("\\n")[0]);answer.setText(title+"\\n\\n"+detail);meta.setText("Telefon komutu · 1.8.0");}});
        if(WakeWordService.enabled(this)){
            if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)WakeWordService.ensureStarted(this);
            else requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},813);
        }
        handleWakeIntent(getIntent());handleDirectIntent(getIntent());
    }

'''
s=s[:start]+new_oncreate+s[end:]

# Insert the actual premium JARVIS home UI helpers before onNewIntent/button.
insert_at=s.find('    @Override protected void onNewIntent(Intent intent)')
if insert_at<0: insert_at=s.index('    private Button button(String title,View.OnClickListener action)')
helpers=r'''    private int dp(int v){return (int)(v*getResources().getDisplayMetrics().density+0.5f);}
    private android.graphics.drawable.GradientDrawable panelBg(int fill,int stroke,int radius){android.graphics.drawable.GradientDrawable g=new android.graphics.drawable.GradientDrawable();g.setColor(fill);g.setCornerRadius(dp(radius));if(stroke!=0)g.setStroke(dp(1),stroke);return g;}
    private TextView uiText(String text,float size,int color){TextView t=new TextView(this);t.setText(text);t.setTextSize(size);t.setTextColor(color);t.setGravity(Gravity.CENTER);t.setIncludeFontPadding(false);return t;}
    private TextView drawerButton(String text,final Runnable run){TextView t=uiText(text,17,0xffdff5ff);t.setGravity(Gravity.CENTER);t.setPadding(dp(12),dp(20),dp(12),dp(20));t.setBackground(panelBg(0x22051a2d,0xff1c9cff,18));t.setOnClickListener(new View.OnClickListener(){public void onClick(View v){toggleJarvisDrawer(false);if(run!=null)run.run();}});return t;}
    private void toggleJarvisDrawer(boolean forceOpen){if(jarvisDrawer==null)return;boolean open=forceOpen||!jarvisDrawerOpen;jarvisDrawerOpen=open;float x=open?0f:dp(142);jarvisDrawer.animate().translationX(x).setDuration(230).start();}
    private void showJarvisChat(){String cmd=textAt(2001);String ans=answer==null?"":answer.getText().toString();String more=meta==null?"":meta.getText().toString();new AlertDialog.Builder(this).setTitle("Sohbet").setMessage("Komut: "+(cmd.length()==0?"—":cmd)+"\\n\\nCevap: "+(ans.length()==0?"—":ans)+(more.length()==0?"":"\\n\\n"+more)).setPositiveButton("Kapat",null).show();}
    private void buildJarvisHomeUi(){
        getWindow().setStatusBarColor(0xff020913);getWindow().setNavigationBarColor(0xff020913);
        final android.widget.FrameLayout frame=new android.widget.FrameLayout(this);frame.setBackgroundColor(0xff020913);
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);scroll.setOverScrollMode(View.OVER_SCROLL_NEVER);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setGravity(Gravity.CENTER_HORIZONTAL);root.setPadding(dp(22),dp(22),dp(22),dp(28));scroll.addView(root,new ScrollView.LayoutParams(-1,-1));
        frame.addView(scroll,new android.widget.FrameLayout.LayoutParams(-1,-1));

        TextView title=uiText("J A R V I S",29,0xffe7f7ff);title.setLetterSpacing(0.16f);root.addView(title,new LinearLayout.LayoutParams(-1,dp(48)));
        TextView sub=uiText("Kişisel Yapay Zeka Asistanın",14,0xff8ebbd7);sub.setLetterSpacing(0.08f);root.addView(sub,new LinearLayout.LayoutParams(-1,dp(30)));
        View topLine=new View(this);topLine.setBackgroundColor(0xff149cff);LinearLayout.LayoutParams tlp=new LinearLayout.LayoutParams(dp(72),dp(2));tlp.topMargin=dp(4);tlp.bottomMargin=dp(16);root.addView(topLine,tlp);

        ImageView core=new ImageView(this);core.setScaleType(ImageView.ScaleType.CENTER_CROP);core.setAdjustViewBounds(true);try{java.io.InputStream in=getAssets().open("jarvis_core.webp");core.setImageBitmap(android.graphics.BitmapFactory.decodeStream(in));in.close();}catch(Exception ignored){}
        LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(dp(330),dp(330));cp.topMargin=dp(4);cp.bottomMargin=dp(10);root.addView(core,cp);

        TextView hello=uiText("Merhaba Hakan",27,0xfff2f7fb);hello.setLetterSpacing(0.08f);root.addView(hello,new LinearLayout.LayoutParams(-1,dp(48)));
        recognitionStatus=uiText("Hazırım.",18,0xff8ebbd7);recognitionStatus.setLetterSpacing(0.08f);root.addView(recognitionStatus,new LinearLayout.LayoutParams(-1,dp(38)));

        LinearLayout commandCard=new LinearLayout(this);commandCard.setGravity(Gravity.CENTER_VERTICAL);commandCard.setPadding(dp(16),dp(12),dp(16),dp(12));commandCard.setBackground(panelBg(0x66101b27,0xff167fc7,22));
        TextView commandLabel=uiText("Komut:",15,0xff70bfff);commandLabel.setGravity(Gravity.CENTER_VERTICAL|Gravity.LEFT);commandCard.addView(commandLabel,new LinearLayout.LayoutParams(dp(66),-2));
        TextView command=new TextView(this);command.setId(2001);command.setText("—");command.setTextColor(0xffedf8ff);command.setTextSize(16);command.setSingleLine(true);command.setEllipsize(android.text.TextUtils.TruncateAt.END);commandCard.addView(command,new LinearLayout.LayoutParams(0,-2,1));
        LinearLayout.LayoutParams cardLp=new LinearLayout.LayoutParams(-1,dp(62));cardLp.topMargin=dp(8);root.addView(commandCard,cardLp);

        LinearLayout answerCard=new LinearLayout(this);answerCard.setGravity(Gravity.CENTER_VERTICAL);answerCard.setPadding(dp(16),dp(10),dp(16),dp(10));answerCard.setBackground(panelBg(0x66101b27,0xff167fc7,22));
        TextView answerLabel=uiText("Cevap:",15,0xff70bfff);answerLabel.setGravity(Gravity.TOP|Gravity.LEFT);answerCard.addView(answerLabel,new LinearLayout.LayoutParams(dp(66),-2));
        answer=new TextView(this);answer.setText("—");answer.setTextColor(0xffedf8ff);answer.setTextSize(16);answer.setMaxLines(2);answer.setEllipsize(android.text.TextUtils.TruncateAt.END);answer.setTextIsSelectable(true);answerCard.addView(answer,new LinearLayout.LayoutParams(0,-2,1));
        LinearLayout.LayoutParams ansLp=new LinearLayout.LayoutParams(-1,dp(74));ansLp.topMargin=dp(10);root.addView(answerCard,ansLp);

        // Hidden technical views preserve the legacy command engine's IDs and state without cluttering the new home screen.
        TextView intentView=new TextView(this);intentView.setId(2002);intentView.setVisibility(View.GONE);root.addView(intentView,new LinearLayout.LayoutParams(1,1));
        TextView detailView=new TextView(this);detailView.setId(2003);detailView.setVisibility(View.GONE);root.addView(detailView,new LinearLayout.LayoutParams(1,1));
        TextView netView=new TextView(this);netView.setId(2006);netView.setVisibility(View.GONE);root.addView(netView,new LinearLayout.LayoutParams(1,1));
        meta=new TextView(this);meta.setVisibility(View.GONE);meta.setTextIsSelectable(true);root.addView(meta,new LinearLayout.LayoutParams(1,1));
        heard=new TextView(this);heard.setVisibility(View.GONE);heard.setText("Duyduğum: —");root.addView(heard,new LinearLayout.LayoutParams(1,1));
        voiceStatus=new TextView(this);voiceStatus.setVisibility(View.GONE);root.addView(voiceStatus,new LinearLayout.LayoutParams(1,1));
        micLevel=new ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal);micLevel.setMax(100);micLevel.setVisibility(View.GONE);root.addView(micLevel,new LinearLayout.LayoutParams(1,1));

        retry=button("YENİDEN DENE",new View.OnClickListener(){public void onClick(View v){if(last!=null)request(last);}});retry.setVisibility(View.GONE);
        cancel=button("İPTAL",new View.OnClickListener(){public void onClick(View v){cancelWork();if(voice!=null)voice.beginTurn();local("İptal edildi","Yerel komutları kullanmaya devam edebilirsiniz.");}});cancel.setVisibility(View.GONE);
        LinearLayout actions=new LinearLayout(this);actions.setGravity(Gravity.CENTER);actions.addView(retry);actions.addView(cancel);root.addView(actions,new LinearLayout.LayoutParams(-1,-2));

        ImageButton mic=new ImageButton(this);mic.setImageResource(android.R.drawable.ic_btn_speak_now);mic.setColorFilter(0xffe9f9ff);mic.setScaleType(ImageView.ScaleType.CENTER_INSIDE);mic.setPadding(dp(24),dp(24),dp(24),dp(24));mic.setBackground(panelBg(0xff071421,0xff1b9fff,80));mic.setOnClickListener(this);
        LinearLayout.LayoutParams mlp=new LinearLayout.LayoutParams(dp(92),dp(92));mlp.topMargin=dp(20);root.addView(mic,mlp);
        TextView micHint=uiText("",12,0xff4c93bf);root.addView(micHint,new LinearLayout.LayoutParams(-1,dp(12)));

        jarvisDrawer=new LinearLayout(this);jarvisDrawer.setOrientation(LinearLayout.VERTICAL);jarvisDrawer.setGravity(Gravity.CENTER);jarvisDrawer.setPadding(dp(10),dp(14),dp(10),dp(14));jarvisDrawer.setBackground(panelBg(0xee03101d,0xff138ee7,26));
        jarvisDrawer.addView(drawerButton("◯\nSohbet",new Runnable(){public void run(){showJarvisChat();}}),new LinearLayout.LayoutParams(-1,dp(104)));
        jarvisDrawer.addView(drawerButton("✎\nYaz",new Runnable(){public void run(){showInput();}}),new LinearLayout.LayoutParams(-1,dp(104)));
        jarvisDrawer.addView(drawerButton("⚙\nAyarlar",new Runnable(){public void run(){showSettings();}}),new LinearLayout.LayoutParams(-1,dp(104)));
        android.widget.FrameLayout.LayoutParams dlp=new android.widget.FrameLayout.LayoutParams(dp(150),dp(344),Gravity.RIGHT|Gravity.CENTER_VERTICAL);dlp.rightMargin=dp(-4);frame.addView(jarvisDrawer,dlp);jarvisDrawer.setTranslationX(dp(142));
        TextView tab=uiText("‹",34,0xffe9f9ff);tab.setBackground(panelBg(0xee061525,0xff168ee2,18));tab.setOnClickListener(new View.OnClickListener(){public void onClick(View v){toggleJarvisDrawer(false);}});android.widget.FrameLayout.LayoutParams tpl=new android.widget.FrameLayout.LayoutParams(dp(42),dp(86),Gravity.RIGHT|Gravity.CENTER_VERTICAL);tpl.rightMargin=dp(0);frame.addView(tab,tpl);
        setContentView(frame);
    }

'''
s=s[:insert_at]+helpers+s[insert_at:]

# Keep alarm and alternate listening controls accessible inside Settings, not on the minimalist home screen.
settings_marker='        layout.addView(button("KONUŞMA TANIMA AYARLARI",new View.OnClickListener(){public void onClick(View v){try{startActivity(new Intent(android.provider.Settings.ACTION_VOICE_INPUT_SETTINGS));}catch(Exception e){try{startActivity(new Intent(android.provider.Settings.ACTION_SETTINGS));}catch(Exception ignored){}}}}));'
if settings_marker in s and 'layout.addView(button("ALARMLARIM"' not in s:
    extra='''        layout.addView(button("ALARMLARIM",new View.OnClickListener(){public void onClick(View v){showAlarms();}}));\n        layout.addView(button("ALTERNATİF DİNLEME",new View.OnClickListener(){public void onClick(View v){alternativeListening();}}));\n'''
    s=s.replace(settings_marker,extra+settings_marker,1)

# UI version strings.
s=s.replace('JARVIS 1.7.0 · ONE BREATH COMMAND','JARVIS 1.8.0 · JARVIS HOME')
s=s.replace('Telefon komutu · 1.7.0','Telefon komutu · 1.8.0')
h.write_text(s,encoding='utf-8')

# Reproduce the phone-proven v1.7.6 microphone/media-safe wake logic at source level.
o=java/'OpenWakeWordDetector.java';x=o.read_text(encoding='utf-8')
old='try{if(melSession==null)initModels();initBuffers();if(!initAudioRecord())throw new IllegalStateException("Mikrofon açılamadı");audioLoop();}'
new='try{if(!initAudioRecord())throw new IllegalStateException("Mikrofon açılamadı");if(melSession==null)initModels();initBuffers();audioLoop();}'
if old not in x: raise SystemExit('OpenWake start marker missing')
x=x.replace(old,new,1)
old='registerRecordingDiagnostics(candidate);return true;'
new='candidate.startRecording();return true;'
if old not in x: raise SystemExit('AudioRecord init marker missing')
x=x.replace(old,new,1)
x=x.replace('private void audioLoop(){AudioRecord r=audioRecord;if(r==null)return;r.startRecording();JarvisForensics.event(context,"A","startRecording state="+r.getRecordingState()+" source="+activeSource);','private void audioLoop(){AudioRecord r=audioRecord;if(r==null)return;JarvisForensics.event(context,"A","startRecording state="+r.getRecordingState()+" source="+activeSource);',1)
x=x.replace('if(score>=0.48f){','if(score>=0.42f){',1)
o.write_text(x,encoding='utf-8')

w=java/'WakeWordService.java';x=w.read_text(encoding='utf-8')
if 'new OpenWakeWordDetector(this,0.30f,0.48f,3800L)' not in x: raise SystemExit('Wake threshold marker missing')
x=x.replace('new OpenWakeWordDetector(this,0.30f,0.48f,3800L)','new OpenWakeWordDetector(this,0.15f,0.42f,3800L)',1)
w.write_text(x,encoding='utf-8')

# Manifest: new version, app icon, same package and foreground-service behavior.
m=base/'app/src/main/AndroidManifest.xml';x=m.read_text(encoding='utf-8')
x=re.sub(r'android:versionCode="\d+" android:versionName="[^"]+"','android:versionCode="102" android:versionName="1.8.0"',x,count=1)
if 'android:icon="@drawable/jarvis_icon"' not in x:
    x=x.replace('<application android:label="JARVIS"','<application android:label="JARVIS" android:icon="@drawable/jarvis_icon" android:roundIcon="@drawable/jarvis_icon"',1)
m.write_text(x,encoding='utf-8')

# Gradle metadata is only used as a source sanity check in this build line.
b=base/'app/build.gradle';g=b.read_text(encoding='utf-8')
g=re.sub(r'versionCode\s+\d+','versionCode 102',g,count=1)
g=re.sub(r"versionName\s+'[^']+'","versionName '1.8.0'",g,count=1)
b.write_text(g,encoding='utf-8')

print('JARVIS 1.8.0 patch applied')
