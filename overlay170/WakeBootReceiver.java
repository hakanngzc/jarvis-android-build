package com.hakan.jarvis;
import android.content.*;
public final class WakeBootReceiver extends BroadcastReceiver{
 @Override public void onReceive(Context c,Intent i){String a=i==null?"":i.getAction();if(Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)||Intent.ACTION_BOOT_COMPLETED.equals(a)){try{WakeWordService.ensureStarted(c);}catch(Exception ignored){}}}
}