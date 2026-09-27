package com.hakan.jarvis;

import android.app.*;
import android.content.*;
import android.media.*;
import android.os.*;
import android.widget.*;
import java.util.*;

public final class WakeWordEnrollment {
    public interface Listener{void done(boolean ok,String detail);}
    private static volatile boolean running;
    private WakeWordEnrollment(){}

    public static void start(final Activity activity,final Listener listener){
        if(running)return;running=true;
        final Handler main=new Handler(Looper.getMainLooper());
        final LinearLayout box=new LinearLayout(activity);box.setOrientation(LinearLayout.VERTICAL);box.setPadding(36,24,36,18);
        final TextView text=new TextView(activity);text.setTextSize(18);text.setText("Hazırlanıyor…");box.addView(text);
        final ProgressBar progress=new ProgressBar(activity,null,android.R.attr.progressBarStyleHorizontal);progress.setMax(3);box.addView(progress);
        final AlertDialog dialog=new AlertDialog.Builder(activity).setTitle("JARVIS sesini öğreniyor").setMessage("Telefonu normal konuşma mesafesinde tutun. Üç kez yalnızca ‘Jarvis’ diyeceksiniz.").setView(box).setNegativeButton("İptal",null).create();
        dialog.setCanceledOnTouchOutside(false);dialog.show();
        final boolean[] cancelled=new boolean[]{false};
        dialog.setOnCancelListener(new DialogInterface.OnCancelListener(){public void onCancel(DialogInterface d){cancelled[0]=true;}});
        dialog.getButton(DialogInterface.BUTTON_NEGATIVE).setOnClickListener(v->{cancelled[0]=true;dialog.dismiss();});
        new Thread(new Runnable(){public void run(){
            boolean ok=false;String detail="Kalibrasyon tamamlanamadı.";
            AudioRecord record=null;
            try{
                WakeWordDetector.clear(activity);
                int min=AudioRecord.getMinBufferSize(WakeSignal.SAMPLE_RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
                int size=Math.max(min*2,4096);
                try{record=new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,WakeSignal.SAMPLE_RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,size);}catch(Exception e){record=new AudioRecord(MediaRecorder.AudioSource.MIC,WakeSignal.SAMPLE_RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,size);}
                if(record.getState()!=AudioRecord.STATE_INITIALIZED)throw new IllegalStateException("Mikrofon başlatılamadı");
                for(int i=1;i<=3&&!cancelled[0];i++){
                    final int index=i;main.post(new Runnable(){public void run(){text.setText(index+"/3 · Şimdi yalnızca ‘Jarvis’ deyin");progress.setProgress(index-1);}});
                    ToneGenerator tone=null;try{tone=new ToneGenerator(AudioManager.STREAM_MUSIC,55);tone.startTone(ToneGenerator.TONE_PROP_BEEP,120);Thread.sleep(160);}catch(Exception ignored){}finally{if(tone!=null)try{tone.release();}catch(Exception ignored){}}
                    Thread.sleep(220);
                    short[] sample=capture(record,cancelled);
                    sample=WakeSignal.trim(sample);
                    if(sample.length<WakeSignal.SAMPLE_RATE*35/100||sample.length>WakeSignal.SAMPLE_RATE*25/10){i--;main.post(new Runnable(){public void run(){text.setText("Ses net alınamadı · tekrar ‘Jarvis’ deyin");}});Thread.sleep(650);continue;}
                    WakeWordDetector.save(activity,i,sample);
                    main.post(new Runnable(){public void run(){progress.setProgress(index);}});Thread.sleep(450);
                }
                if(!cancelled[0]&&WakeWordDetector.hasEnrollment(activity)){
                    double th=WakeWordDetector.calibrate(activity);
                    short[][] t=WakeWordDetector.loadAll(activity);
                    double d01=WakeSignal.distance(t[0],t[1]),d02=WakeSignal.distance(t[0],t[2]),d12=WakeSignal.distance(t[1],t[2]);
                    double worst=Math.max(d01,Math.max(d02,d12));
                    if(worst>th*1.45){WakeWordDetector.clear(activity);detail="Üç kayıt birbirine yeterince benzemedi. Sessiz bir ortamda tekrar deneyin.";}
                    else{ok=true;detail="Wake word hazır · eşik "+String.format(Locale.US,"%.2f",th);}
                }
            }catch(Exception e){detail=e.getMessage()==null?"Mikrofon kalibrasyon hatası":e.getMessage();WakeWordDetector.clear(activity);}
            finally{if(record!=null){try{record.release();}catch(Exception ignored){}}running=false;}
            final boolean result=ok;final String msg=detail;main.post(new Runnable(){public void run(){if(dialog.isShowing())dialog.dismiss();listener.done(result,msg);}});
        }}).start();
    }

    private static short[] capture(AudioRecord record,boolean[] cancelled)throws Exception{
        final int chunk=320;short[] buf=new short[chunk];ArrayList<short[]> blocks=new ArrayList<short[]>();
        short[][] preroll=new short[10][];int pre=0;double noise=120;boolean speech=false;int hot=0,silent=0,speechSamples=0;
        record.startRecording();long deadline=System.currentTimeMillis()+4500;
        try{
            while(!cancelled[0]&&System.currentTimeMillis()<deadline){
                int n=record.read(buf,0,buf.length);if(n<=0)continue;short[] b=Arrays.copyOf(buf,n);double rms=rms(b,n);
                if(!speech){noise=noise*0.94+rms*0.06;preroll[pre++%preroll.length]=b;double gate=Math.max(260,noise*2.5);if(rms>gate)hot++;else hot=Math.max(0,hot-1);if(hot>=2){speech=true;for(int k=0;k<preroll.length;k++){short[] p=preroll[(pre+k)%preroll.length];if(p!=null){blocks.add(p);speechSamples+=p.length;}}blocks.add(b);speechSamples+=n;}}
                else{blocks.add(b);speechSamples+=n;double gate=Math.max(220,noise*1.65);if(rms<gate)silent++;else silent=0;if((silent>=22&&speechSamples>WakeSignal.SAMPLE_RATE*45/100)||speechSamples>WakeSignal.SAMPLE_RATE*25/10)break;}
            }
        }finally{try{record.stop();}catch(Exception ignored){}}
        int total=0;for(short[] b:blocks)total+=b.length;short[] out=new short[total];int at=0;for(short[] b:blocks){System.arraycopy(b,0,out,at,b.length);at+=b.length;}return out;
    }
    private static double rms(short[] b,int n){double s=1;for(int i=0;i<n;i++){double v=b[i];s+=v*v;}return Math.sqrt(s/Math.max(1,n));}
}
