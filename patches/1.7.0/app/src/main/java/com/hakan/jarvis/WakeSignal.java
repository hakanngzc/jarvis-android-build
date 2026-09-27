package com.hakan.jarvis;

import java.util.*;

/**
 * Pure-Java wake-word signal features + DTW matcher.
 * No cloud, no Android SpeechRecognizer and no native model is required.
 * Enrollment and runtime audio are both 16 kHz mono PCM16.
 */
public final class WakeSignal {
    public static final int SAMPLE_RATE = 16000;
    private static final int FRAME = 400;
    private static final int HOP = 160;
    private static final double[] FREQS = {300,450,650,900,1200,1600,2100,2800,3600,4800};
    private WakeSignal() {}

    public static short[] trim(short[] input) {
        if (input == null || input.length == 0) return new short[0];
        int max = 0;
        for (short v : input) max = Math.max(max, Math.abs((int)v));
        if (max < 180) return new short[0];
        int gate = Math.max(180, (int)(max * 0.075));
        int pad = SAMPLE_RATE / 12;
        int first = 0, last = input.length - 1;
        while (first < input.length && Math.abs((int)input[first]) < gate) first++;
        while (last > first && Math.abs((int)input[last]) < gate) last--;
        first = Math.max(0, first - pad);
        last = Math.min(input.length - 1, last + pad);
        if (last - first < SAMPLE_RATE / 4) return new short[0];
        return Arrays.copyOfRange(input, first, last + 1);
    }

    public static double distance(short[] a, short[] b) {
        short[] ta = trim(a), tb = trim(b);
        if (ta.length == 0 || tb.length == 0) return 99.0;
        double ratio = (double)Math.max(ta.length, tb.length) / Math.max(1, Math.min(ta.length, tb.length));
        if (ratio > 1.95) return 99.0;
        float[][] fa = features(ta), fb = features(tb);
        if (fa.length < 12 || fb.length < 12) return 99.0;
        return dtw(fa, fb);
    }

    public static double enrollmentThreshold(short[][] templates) {
        if (templates == null || templates.length < 3) return 0.82;
        double[] d = new double[]{
            distance(templates[0], templates[1]),
            distance(templates[0], templates[2]),
            distance(templates[1], templates[2])
        };
        Arrays.sort(d);
        double base = d[1];
        if (!Double.isFinite(base) || base >= 90) return 0.82;
        return clamp(base * 1.70 + 0.12, 0.42, 1.28);
    }

    public static boolean matches(short[][] templates, short[] candidate, double threshold) {
        if (templates == null || templates.length < 3 || candidate == null) return false;
        short[] c = trim(candidate);
        if (c.length < SAMPLE_RATE * 35 / 100 || c.length > SAMPLE_RATE * 26 / 10) return false;
        int[] lens = new int[]{trim(templates[0]).length, trim(templates[1]).length, trim(templates[2]).length};
        Arrays.sort(lens);
        if (lens[1] <= 0) return false;
        double lr = (double)c.length / lens[1];
        if (lr < 0.48 || lr > 1.75) return false;
        double[] d = new double[3];
        for (int i=0;i<3;i++) d[i]=distance(templates[i],c);
        Arrays.sort(d);
        return d[1] <= threshold && d[0] <= threshold * 0.94;
    }

    static float[][] features(short[] pcm) {
        if (pcm.length < FRAME) return new float[0][0];
        int count = 1 + (pcm.length - FRAME) / HOP;
        int dims = 2 + FREQS.length;
        float[][] out = new float[count][dims];
        double[] window = new double[FRAME];
        for (int n=0;n<FRAME;n++) window[n] = 0.54 - 0.46 * Math.cos(2.0*Math.PI*n/(FRAME-1));
        for (int f=0;f<count;f++) {
            int off=f*HOP;
            double energy=1.0;
            int zc=0;
            double prev=pcm[off];
            for (int i=0;i<FRAME;i++) {
                double x=pcm[off+i]*window[i];
                energy += x*x;
                if (i>0 && ((pcm[off+i]>=0)!=(prev>=0))) zc++;
                prev=pcm[off+i];
            }
            out[f][0]=(float)Math.log(energy/FRAME+1.0);
            out[f][1]=(float)zc/FRAME;
            for (int k=0;k<FREQS.length;k++) {
                double omega=2.0*Math.PI*FREQS[k]/SAMPLE_RATE;
                double coeff=2.0*Math.cos(omega), q0=0,q1=0,q2=0;
                for (int i=0;i<FRAME;i++) {
                    double x=pcm[off+i]*window[i];
                    q0=coeff*q1-q2+x; q2=q1; q1=q0;
                }
                double power=q1*q1+q2*q2-coeff*q1*q2;
                out[f][2+k]=(float)Math.log(Math.max(1.0,power/FRAME));
            }
        }
        cmvn(out);
        addDelta(out);
        return out;
    }

    private static void cmvn(float[][] f) {
        if (f.length==0) return;
        int d=f[0].length;
        for (int j=0;j<d;j++) {
            double mean=0;
            for (float[] row:f) mean+=row[j];
            mean/=f.length;
            double var=1e-6;
            for (float[] row:f){double x=row[j]-mean;var+=x*x;}
            double sd=Math.sqrt(var/f.length);
            for (float[] row:f) row[j]=(float)((row[j]-mean)/sd);
        }
    }

    private static void addDelta(float[][] f) {
        if (f.length<3) return;
        float[][] copy=new float[f.length][f[0].length];
        for(int i=0;i<f.length;i++) System.arraycopy(f[i],0,copy[i],0,f[i].length);
        for(int i=1;i<f.length-1;i++) for(int j=0;j<f[i].length;j++) f[i][j]=(float)(copy[i][j]+0.22*(copy[i+1][j]-copy[i-1][j]));
    }

    static double dtw(float[][] a, float[][] b) {
        int n=a.length,m=b.length;
        int band=Math.max(Math.abs(n-m)+4,(int)(Math.max(n,m)*0.28));
        double inf=1e30;
        double[] prev=new double[m+1],cur=new double[m+1];
        Arrays.fill(prev,inf);prev[0]=0;
        for(int i=1;i<=n;i++){
            Arrays.fill(cur,inf);
            int lo=Math.max(1,i-band),hi=Math.min(m,i+band);
            for(int j=lo;j<=hi;j++){
                double cost=frameDistance(a[i-1],b[j-1]);
                double best=Math.min(prev[j],Math.min(cur[j-1],prev[j-1]));
                cur[j]=cost+best;
            }
            double[] t=prev;prev=cur;cur=t;
        }
        return prev[m]/Math.max(n,m);
    }

    private static double frameDistance(float[] a,float[] b){
        double s=0;int d=Math.min(a.length,b.length);
        for(int i=0;i<d;i++){double x=a[i]-b[i];s+=x*x;}
        return Math.sqrt(s/Math.max(1,d));
    }

    private static double clamp(double x,double lo,double hi){return Math.max(lo,Math.min(hi,x));}
}
