package com.hakan.jarvis;

import android.content.*;
import java.io.*;

public final class WakeWordDetector {
    private static final String DIR="wakeword";
    private WakeWordDetector(){}

    public static File dir(Context c){File d=new File(c.getFilesDir(),DIR);d.mkdirs();return d;}
    public static boolean hasEnrollment(Context c){for(int i=1;i<=3;i++){File f=new File(dir(c),"wake_"+i+".pcm");if(!f.isFile()||f.length()<8000)return false;}return true;}
    public static void clear(Context c){File[] fs=dir(c).listFiles();if(fs!=null)for(File f:fs)f.delete();c.getSharedPreferences("jarvis_hybrid",0).edit().remove("wake_threshold").apply();}
    public static void save(Context c,int index,short[] pcm)throws IOException{File f=new File(dir(c),"wake_"+index+".pcm");DataOutputStream out=new DataOutputStream(new BufferedOutputStream(new FileOutputStream(f)));try{for(short s:pcm){out.writeByte(s&255);out.writeByte((s>>>8)&255);}}finally{out.close();}}
    public static short[] load(Context c,int index)throws IOException{File f=new File(dir(c),"wake_"+index+".pcm");byte[] b=new byte[(int)f.length()];DataInputStream in=new DataInputStream(new BufferedInputStream(new FileInputStream(f)));try{in.readFully(b);}finally{in.close();}short[] s=new short[b.length/2];for(int i=0;i<s.length;i++)s[i]=(short)((b[i*2]&255)|(b[i*2+1]<<8));return s;}
    public static short[][] loadAll(Context c)throws IOException{return new short[][]{load(c,1),load(c,2),load(c,3)};}
    public static double calibrate(Context c)throws IOException{short[][] t=loadAll(c);double threshold=WakeSignal.enrollmentThreshold(t);c.getSharedPreferences("jarvis_hybrid",0).edit().putFloat("wake_threshold",(float)threshold).apply();return threshold;}
    public static boolean isWake(Context c,short[] candidate){try{if(!hasEnrollment(c))return false;double threshold=c.getSharedPreferences("jarvis_hybrid",0).getFloat("wake_threshold",0.82f);return WakeSignal.matches(loadAll(c),candidate,threshold);}catch(Exception e){return false;}}
}
