package com.hakan.jarvis;
import android.content.*;
import android.content.pm.PackageManager;
import android.Manifest;
public final class WakeWordBootReceiver extends BroadcastReceiver{
 public void onReceive(Context c,Intent i){try{if(c.getSharedPreferences("jarvis_hybrid",0).getBoolean("wake_enabled",false)&&c.checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED&&WakeWordDetector.hasEnrollment(c))WakeWordService.start(c);}catch(Exception ignored){}}
}
