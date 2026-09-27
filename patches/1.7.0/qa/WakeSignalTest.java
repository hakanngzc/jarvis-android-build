import com.hakan.jarvis.WakeSignal;
import java.util.*;
public class WakeSignalTest {
 static short[] phrase(double stretch,int noise,int seed){
  int sr=16000; int n=(int)(sr*1.15*stretch); short[] x=new short[n]; Random r=new Random(seed);
  for(int i=0;i<n;i++){
   double t=i/(double)sr/stretch; double f=t<0.32?430:t<0.68?720:520; double env=Math.sin(Math.PI*Math.min(1.0,Math.max(0.0,t/1.15)));
   double v=9000*Math.sin(2*Math.PI*f*t)+3200*Math.sin(2*Math.PI*(f*2.1)*t)+1800*Math.sin(2*Math.PI*(f*3.0)*t);
   v*=0.55+0.45*env; v+=noise*r.nextGaussian(); x[i]=(short)Math.max(-32768,Math.min(32767,(int)v));
  }return x;
 }
 static short[] noise(){Random r=new Random(99);short[] x=new short[18000];for(int i=0;i<x.length;i++)x[i]=(short)(r.nextGaussian()*5500);return x;}
 public static void main(String[] args){
  short[][] t={phrase(0.95,300,1),phrase(1.02,350,2),phrase(1.08,280,3)};
  double th=WakeSignal.enrollmentThreshold(t);
  short[] good=phrase(1.00,450,9), bad=noise();
  if(!WakeSignal.matches(t,good,th))throw new AssertionError("good rejected");
  if(WakeSignal.matches(t,bad,th))throw new AssertionError("noise accepted");
  System.out.println("WakeSignalTest PASS threshold="+th);
 }
}
