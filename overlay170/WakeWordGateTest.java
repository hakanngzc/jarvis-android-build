import com.hakan.jarvis.WakeWordGate;
public final class WakeWordGateTest{
 private static int p=0,f=0;private static void ok(String n,boolean x){if(x){System.out.println("PASS "+n);p++;}else{System.out.println("FAIL "+n);f++;}}
 public static void main(String[] a){WakeWordGate g=new WakeWordGate(.18f,.48f,5,2,3200L);ok("single weak rejected",!g.accept(.19f,10000));ok("accent vote accepts two moderate peaks",g.accept(.23f,10080));ok("debounce blocks immediate retrigger",!g.accept(.70f,11000));ok("strong peak accepted after debounce",g.accept(.50f,13301));g.reset();ok("noise sequence rejected",!g.accept(.05f,20000)&&!g.accept(.12f,20080)&&!g.accept(.17f,20160));ok("spaced moderate peaks inside window",!g.accept(.21f,20240)&&!g.accept(.10f,20320)&&g.accept(.20f,20400));System.out.println("TOTAL "+(p+f)+" PASS "+p+" FAIL "+f);if(f!=0)System.exit(1);}
}
