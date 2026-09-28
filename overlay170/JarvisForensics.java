package com.hakan.jarvis;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.SystemClock;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

public final class JarvisForensics {
 private static final String PREF="jarvis_hybrid", KEY_LOG="wake_forensic_log";
 private JarvisForensics(){}
 public static synchronized void event(Context c,String area,String msg){
  if(c==null)return;
  String a=area==null?"?":area.trim();
  String m=msg==null?"":msg.replace('\n',' ').replace('\r',' ');
  String ts=new SimpleDateFormat("HH:mm:ss.SSS",Locale.US).format(new Date());
  String line=ts+" +"+SystemClock.elapsedRealtime()+" ["+a+"] "+m;
  SharedPreferences p=c.getApplicationContext().getSharedPreferences(PREF,Context.MODE_PRIVATE);
  String old=p.getString(KEY_LOG,"");
  String merged=old.length()==0?line:old+"\n"+line;
  String[] rows=merged.split("\n");
  if(rows.length>48){StringBuilder b=new StringBuilder();for(int i=rows.length-48;i<rows.length;i++){if(b.length()>0)b.append('\n');b.append(rows[i]);}merged=b.toString();}
  p.edit().putString(KEY_LOG,merged).putString("wake_forensic_last",line).putString("wake_forensic_last_"+a,line).apply();
 }
 public static String tail(Context c,int n){
  if(c==null)return "";
  String log=c.getApplicationContext().getSharedPreferences(PREF,Context.MODE_PRIVATE).getString(KEY_LOG,"");
  if(log.length()==0)return "FORENSIC: kayıt yok";
  String[] rows=log.split("\n");StringBuilder b=new StringBuilder();
  for(int i=Math.max(0,rows.length-Math.max(1,n));i<rows.length;i++){if(b.length()>0)b.append('\n');b.append(rows[i]);}
  return b.toString();
 }
 public static String caller(){
  StackTraceElement[] st=Thread.currentThread().getStackTrace();
  for(StackTraceElement e:st){String c=e.getClassName(),m=e.getMethodName();if(c.startsWith("com.hakan.jarvis.")&&!c.endsWith("JarvisForensics")&&!m.equals("stopRecognition")&&!m.equals("event")&&!m.equals("caller"))return e.getClassName().substring(e.getClassName().lastIndexOf('.')+1)+"#"+m+":"+e.getLineNumber();}
  return "?";
 }
}
