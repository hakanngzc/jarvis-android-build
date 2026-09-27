package com.hakan.jarvis;

import android.Manifest;
import android.app.*;
import android.content.*;
import android.content.pm.PackageManager;
import android.media.*;
import android.os.*;
import java.util.*;

public final class WakeWordService extends Service {
    public static final String ACTION_START="com.hakan.jarvis.wake.START";
    public static final String ACTION_STOP="com.hakan.jarvis.wake.STOP";
    public static final String ACTION_PAUSE="com.hakan.jarvis.wake.PAUSE";
    public static final String ACTION_RESUME="com.hakan.jarvis.wake.RESUME";
    public static final String EXTRA_PAUSE_MS="pause_ms";
    public static final String EXTRA_WAKE_TRIGGER="jarvis_wake_trigger";
    public static final int NOTIFY_ID=1700,WAKE_NOTIFY_ID=1701;
    private static final String CHANNEL="jarvis_wake_service",WAKE_CHANNEL="jarvis_wake_event";

    private volatile boolean stopping;
    private volatile long pausedUntil;
    private Thread worker;
    private AudioRecord recorder;
    private PowerManager.WakeLock cpuLock;

    public static void start(Context c){Intent i=new Intent(c,WakeWordService.class).setAction(ACTION_START);try{if(Build.VERSION.SDK_INT>=26)c.startForegroundService(i);else c.startService(i);}catch(Exception ignored){}}
    public static void stop(Context c){try{c.startService(new Intent(c,WakeWordService.class).setAction(ACTION_STOP));}catch(Exception ignored){try{c.stopService(new Intent(c,WakeWordService.class));}catch(Exception ignored2){}}}
    public static void pause(Context c,long ms){try{Intent i=new Intent(c,WakeWordService.class).setAction(ACTION_PAUSE).putExtra(EXTRA_PAUSE_MS,ms);c.startService(i);}catch(Exception ignored){}}
    public static void resume(Context c){try{c.startService(new Intent(c,WakeWordService.class).setAction(ACTION_RESUME));}catch(Exception ignored){}}
    public static void clearWakeNotification(Context c){try{((NotificationManager)c.getSystemService(NOTIFICATION_SERVICE)).cancel(WAKE_NOTIFY_ID);}catch(Exception ignored){}}

    @Override public void onCreate(){super.onCreate();createChannels();startForeground(NOTIFY_ID,notification("JARVIS hazırlanıyor","Wake word servisi başlatılıyor…",false,null));acquireCpu();}
    @Override public int onStartCommand(Intent intent,int flags,int startId){
        String action=intent==null?ACTION_START:intent.getAction();
        if(ACTION_STOP.equals(action)){getSharedPreferences("jarvis_hybrid",0).edit().putBoolean("wake_enabled",false).apply();shutdown();stopForeground(true);stopSelf();return START_NOT_STICKY;}
        if(ACTION_PAUSE.equals(action)){long ms=intent==null?30000:intent.getLongExtra(EXTRA_PAUSE_MS,30000);pausedUntil=Math.max(pausedUntil,System.currentTimeMillis()+Math.max(1000,ms));stopRecorder();update("JARVIS beklemede","Mikrofon başka bir JARVIS işlemi için geçici olarak bırakıldı.");return START_STICKY;}
        if(ACTION_RESUME.equals(action)){pausedUntil=0;ensureWorker();return START_STICKY;}
        if(!getSharedPreferences("jarvis_hybrid",0).getBoolean("wake_enabled",false)){stopSelf();return START_NOT_STICKY;}
        ensureWorker();return START_STICKY;
    }
    @Override public void onDestroy(){shutdown();releaseCpu();super.onDestroy();}
    @Override public IBinder onBind(Intent i){return null;}
    @Override public void onTaskRemoved(Intent rootIntent){if(getSharedPreferences("jarvis_hybrid",0).getBoolean("wake_enabled",false))start(this);super.onTaskRemoved(rootIntent);}

    private synchronized void ensureWorker(){if(worker!=null&&worker.isAlive())return;stopping=false;worker=new Thread(new Runnable(){public void run(){loop();}},"JarvisWakeWord");worker.start();}
    private void loop(){
        while(!stopping){
            try{
                if(!getSharedPreferences("jarvis_hybrid",0).getBoolean("wake_enabled",false)){Thread.sleep(1200);continue;}
                if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){update("JARVIS wake word kapalı","Mikrofon izni gerekiyor.");Thread.sleep(2500);continue;}
                if(!WakeWordDetector.hasEnrollment(this)){update("JARVIS kalibrasyonu gerekli","Uygulamayı açıp Hibrit Ayarlar > JARVIS SESİNİ ÖĞRET seçeneğini kullanın.");Thread.sleep(2500);continue;}
                long now=System.currentTimeMillis();if(pausedUntil>now){Thread.sleep(Math.min(1200,pausedUntil-now));continue;}else if(pausedUntil!=0)pausedUntil=0;
                listenSession();
            }catch(InterruptedException e){break;}catch(Exception e){update("JARVIS yeniden hazırlanıyor","Mikrofon geçici olarak kullanılamadı.");stopRecorder();try{Thread.sleep(1800);}catch(InterruptedException ie){break;}}
        }
        stopRecorder();
    }

    private void listenSession()throws Exception{
        int min=AudioRecord.getMinBufferSize(WakeSignal.SAMPLE_RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);int size=Math.max(4096,min*2);
        try{recorder=new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,WakeSignal.SAMPLE_RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,size);}catch(Exception e){recorder=new AudioRecord(MediaRecorder.AudioSource.MIC,WakeSignal.SAMPLE_RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,size);}
        if(recorder.getState()!=AudioRecord.STATE_INITIALIZED)throw new IllegalStateException("AudioRecord");
        recorder.startRecording();update("JARVIS aktif","‘Jarvis’ demenizi bekliyor · çevrimdışı");
        short[] buf=new short[320];short[][] pre=new short[10][];int preAt=0;ArrayList<short[]> blocks=new ArrayList<short[]>();double noise=120;boolean speech=false;int hot=0,silent=0,total=0;long cooldown=0;
        while(!stopping&&pausedUntil<=System.currentTimeMillis()&&getSharedPreferences("jarvis_hybrid",0).getBoolean("wake_enabled",false)){
            int n=recorder.read(buf,0,buf.length);if(n<=0)continue;short[] b=Arrays.copyOf(buf,n);double rms=rms(b,n);long now=System.currentTimeMillis();
            if(!speech){noise=noise*0.96+rms*0.04;pre[preAt++%pre.length]=b;double gate=Math.max(260,noise*2.55);if(rms>gate)hot++;else hot=Math.max(0,hot-1);if(hot>=2&&now>cooldown){speech=true;blocks.clear();total=0;for(int k=0;k<pre.length;k++){short[] p=pre[(preAt+k)%pre.length];if(p!=null){blocks.add(p);total+=p.length;}}blocks.add(b);total+=n;silent=0;}}
            else{blocks.add(b);total+=n;double gate=Math.max(220,noise*1.65);if(rms<gate)silent++;else silent=0;if((silent>=20&&total>WakeSignal.SAMPLE_RATE*35/100)||total>WakeSignal.SAMPLE_RATE*27/10){short[] utterance=flatten(blocks,total);speech=false;hot=0;silent=0;blocks.clear();if(WakeWordDetector.isWake(this,utterance)){cooldown=now+5000;triggerWake();return;}}}
        }
        stopRecorder();
    }

    private void triggerWake(){
        pausedUntil=System.currentTimeMillis()+45000;stopRecorder();
        try{PowerManager pm=(PowerManager)getSystemService(POWER_SERVICE);PowerManager.WakeLock w=pm.newWakeLock(PowerManager.SCREEN_BRIGHT_WAKE_LOCK|PowerManager.ACQUIRE_CAUSES_WAKEUP|PowerManager.ON_AFTER_RELEASE,"jarvis:wake-screen");w.acquire(6000);}catch(Exception ignored){}
        Intent launch=new Intent(this,HybridActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP).putExtra(EXTRA_WAKE_TRIGGER,true);
        PendingIntent pi=PendingIntent.getActivity(this,1701,launch,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        Notification n=notification("JARVIS sizi duydu","Komut dinleme açılıyor…",true,pi);((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(WAKE_NOTIFY_ID,n);
        boolean launched=false;try{startActivity(launch);launched=true;}catch(Exception ignored){}
        if(!launched){try{pi.send();}catch(Exception ignored){}}
        update("JARVIS aktif","Wake word algılandı · komut dinleme açılıyor");
    }

    private Notification notification(String title,String text,boolean urgent,PendingIntent content){
        Notification.Builder b=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,urgent?WAKE_CHANNEL:CHANNEL):new Notification.Builder(this);
        b.setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle(title).setContentText(text).setOngoing(!urgent).setOnlyAlertOnce(!urgent).setCategory(Notification.CATEGORY_SERVICE);
        if(content!=null){b.setContentIntent(content);if(urgent)b.setFullScreenIntent(content,true);}
        return b.build();
    }
    private void createChannels(){if(Build.VERSION.SDK_INT<26)return;NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);NotificationChannel low=new NotificationChannel(CHANNEL,"JARVIS Wake Word",NotificationManager.IMPORTANCE_LOW);low.setDescription("Ekran kapalıyken Jarvis uyandırma dinlemesi");nm.createNotificationChannel(low);NotificationChannel high=new NotificationChannel(WAKE_CHANNEL,"JARVIS Uyandırma",NotificationManager.IMPORTANCE_HIGH);high.setDescription("Jarvis wake word algılandığında komut ekranını açar");nm.createNotificationChannel(high);}
    private void update(String title,String text){try{((NotificationManager)getSystemService(NOTIFICATION_SERVICE)).notify(NOTIFY_ID,notification(title,text,false,null));}catch(Exception ignored){}}
    private synchronized void stopRecorder(){AudioRecord r=recorder;recorder=null;if(r!=null){try{r.stop();}catch(Exception ignored){}try{r.release();}catch(Exception ignored){}}}
    private void shutdown(){stopping=true;stopRecorder();Thread t=worker;worker=null;if(t!=null)t.interrupt();}
    private void acquireCpu(){try{PowerManager pm=(PowerManager)getSystemService(POWER_SERVICE);cpuLock=pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,"jarvis:wake-cpu");cpuLock.setReferenceCounted(false);cpuLock.acquire();}catch(Exception ignored){}}
    private void releaseCpu(){try{if(cpuLock!=null&&cpuLock.isHeld())cpuLock.release();}catch(Exception ignored){}cpuLock=null;}
    private static short[] flatten(ArrayList<short[]> blocks,int total){short[] out=new short[total];int at=0;for(short[] b:blocks){System.arraycopy(b,0,out,at,b.length);at+=b.length;}return out;}
    private static double rms(short[] b,int n){double s=1;for(int i=0;i<n;i++){double v=b[i];s+=v*v;}return Math.sqrt(s/Math.max(1,n));}
}
