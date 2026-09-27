from pathlib import Path
import sys
base=Path(sys.argv[1])
h=base/'app/src/main/java/com/hakan/jarvis/HybridActivity.java'
s=h.read_text(encoding='utf-8')
s=s.replace('JARVIS 1.6.4.17 · CONTEXT CHAIN SAFE','JARVIS 1.7.0 · HEY JARVIS TUNED')
lines=s.splitlines();out=[];inserted=False
for line in lines:
    if 'meta.setText("Telefon komutu · 1.6.2")' in line:
        out.append(line.replace('Telefon komutu · 1.6.2','Telefon komutu · 1.7.0'))
        out += ['        if(WakeWordService.enabled(this)){','            if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)WakeWordService.ensureStarted(this);','            else requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},813);','        }','        handleWakeIntent(getIntent());'];inserted=True
    elif line.strip().startswith('@Override protected void onResume(){'):
        out.append('    @Override protected void onResume(){super.onResume();updateHybridStatus();if(!registered){try{registerReceiver(networkReceiver,new IntentFilter(ConnectivityManager.CONNECTIVITY_ACTION));registered=true;}catch(Exception ignored){}}if(getIntent()!=null&&getIntent().getBooleanExtra(WakeWordService.EXTRA_WAKE,false))handleWakeIntent(getIntent());}')
    elif line.strip().startswith('@Override protected void onPause(){'):
        out.append('    @Override protected void onPause(){if(phone!=null)phone.pause();if(registered){try{unregisterReceiver(networkReceiver);}catch(Exception ignored){}registered=false;}stopRecognition();if(voice!=null)voice.stop();deferredAction=null;chainedNext="";WakeWordService.resume(this);super.onPause();}')
    elif line.strip().startswith('private void dispatchSpoken(String raw){'):
        out.append('    private void dispatchSpoken(String raw){spokenCommand=true;try{dispatch(raw);}finally{spokenCommand=false;WakeWordService.resume(this);}}')
    elif line.strip()=='private void beginListening(){':
        out.append(line);out.append('        WakeWordService.pause(this);')
    elif line.strip().startswith('@Override public void onRequestPermissionsResult(int code'):
        out.append('    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] grants){if(phone!=null&&phone.permissions(code,grants))return;if(code==813){if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED)WakeWordService.ensureStarted(this);else prefs.edit().putBoolean("wake_enabled",false).apply();return;}if(code==810){if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED)beginListening();else{WakeWordService.resume(this);local("Mikrofon izni kapalı","YAZ düğmesiyle komut verebilirsiniz. Telefonun uygulama izinlerinden mikrofonu açabilirsiniz.");}return;}super.onRequestPermissionsResult(code,permissions,grants);}')
    elif line.strip().startswith('private void recognitionFailure(int code){'):
        out.append('    private void recognitionFailure(int code){stopRecognition();if(dead)return;recognitionStatus.setText("DİNLEME SONA ERDİ · "+RecognitionConfig.error(code));meta.setText("Tanıma kodu: "+code+" · Son duyulan metin yukarıda.");say("",code==9?"mic_denied":"speech_error",null);WakeWordService.resume(this);}')
    else: out.append(line)
s='\n'.join(out)+'\n'
if not inserted: raise SystemExit('phone insertion failed')
marker='    private Button button(String title,View.OnClickListener action){Button b=new Button(this);b.setText(title);b.setOnClickListener(action);return b;}'
insert='''    @Override protected void onNewIntent(Intent intent){super.onNewIntent(intent);setIntent(intent);handleWakeIntent(intent);}
    private void handleWakeIntent(final Intent intent){
        if(intent==null||!intent.getBooleanExtra(WakeWordService.EXTRA_WAKE,false)||voice==null)return;
        boolean acked=intent.getBooleanExtra(WakeWordService.EXTRA_WAKE_ACKED,false);intent.removeExtra(WakeWordService.EXTRA_WAKE);intent.removeExtra(WakeWordService.EXTRA_WAKE_ACKED);WakeWordService.pause(this);
        try{if(Build.VERSION.SDK_INT>=27){setShowWhenLocked(true);setTurnScreenOn(true);}else getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED|WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);}catch(Exception ignored){}
        recognitionStatus.setText("WAKE WORD ALGILANDI · komut dinleme hazırlanıyor");heard.setText("Duyduğum: Hey Jarvis");
        handler.postDelayed(new Runnable(){public void run(){if(dead)return;if(acked)beginListening();else{voice.beginTurn();say("","wake",new Runnable(){public void run(){if(!dead)beginListening();}});}}},180);
    }
'''
if marker not in s: raise SystemExit('button marker missing')
s=s.replace(marker,insert+marker,1)
cloud='        final CheckBox cloud=new CheckBox(this);cloud.setText("Çevrimiçi ayrıntılı konuşma");cloud.setChecked(prefs.getBoolean("cloud_voice",true));layout.addView(cloud);'
if cloud not in s: raise SystemExit('cloud marker missing')
s=s.replace(cloud,cloud+'\n        final CheckBox wake=new CheckBox(this);wake.setText("Ekran kapalıyken ‘Hey Jarvis’ ile uyan");wake.setChecked(prefs.getBoolean("wake_enabled",true));layout.addView(wake);\n        TextView wakeInfo=new TextView(this);wakeInfo.setText("Wake word tamamen cihazda çalışır. Wake mikrofonu sürekli açık kalır. Hey Jarvis tetiklemesi %30 orta eşik, %45 güçlü eşik ve ses enerjisi doğrulaması kullanır; teşhis özeti doğrulama için korunur.");layout.addView(wakeInfo);',1)
old='prefs.edit().putString("city",c.length()==0?"Kahramanmaraş":c).putBoolean("force_offline",offline.isChecked()).putBoolean("cloud_voice",cloud.isChecked()).apply();cancelWork();stopRecognition();voice.beginTurn();updateHybridStatus();say("","settings_saved",null);'
new='prefs.edit().putString("city",c.length()==0?"Kahramanmaraş":c).putBoolean("force_offline",offline.isChecked()).putBoolean("cloud_voice",cloud.isChecked()).putBoolean("wake_enabled",wake.isChecked()).apply();cancelWork();stopRecognition();voice.beginTurn();updateHybridStatus();if(wake.isChecked()){if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)WakeWordService.ensureStarted(HybridActivity.this);else requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},813);}else WakeWordService.stop(HybridActivity.this);say("","settings_saved",null);'
if old not in s: raise SystemExit('settings marker missing')
s=s.replace(old,new,1);h.write_text(s,encoding='utf-8')
m=base/'app/src/main/AndroidManifest.xml';x=m.read_text(encoding='utf-8')
x=x.replace('android:versionCode="81" android:versionName="1.6.4.16-hybrid-safe01"','android:versionCode="90" android:versionName="1.7.0"')
if 'android.permission.FOREGROUND_SERVICE_MICROPHONE' not in x:x=x.replace('<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />','<uses-permission android:name="android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK" />\n  <uses-permission android:name="android.permission.FOREGROUND_SERVICE_MICROPHONE" />')
x=x.replace('<activity android:name="com.hakan.jarvis.HybridActivity" android:exported="true" android:windowSoftInputMode="adjustResize">','<activity android:name="com.hakan.jarvis.HybridActivity" android:exported="true" android:launchMode="singleTop" android:showWhenLocked="true" android:turnScreenOn="true" android:windowSoftInputMode="adjustResize">')
if 'android:name=".WakeWordService"' not in x:x=x.replace('<service android:name=".AlarmRingService" android:exported="false" android:foregroundServiceType="mediaPlayback" />','<service android:name=".AlarmRingService" android:exported="false" android:foregroundServiceType="mediaPlayback" />\n    <service android:name=".WakeWordService" android:exported="false" android:foregroundServiceType="microphone|mediaPlayback" />\n    <receiver android:name=".WakeBootReceiver" android:exported="false"><intent-filter><action android:name="android.intent.action.BOOT_COMPLETED"/><action android:name="android.intent.action.MY_PACKAGE_REPLACED"/></intent-filter></receiver>')
m.write_text(x,encoding='utf-8')
b=base/'app/build.gradle';g=b.read_text(encoding='utf-8').replace('versionCode 82','versionCode 90').replace("versionName '1.6.4.17-context-chain-src1'","versionName '1.7.0'");b.write_text(g,encoding='utf-8')
