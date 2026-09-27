import com.hakan.jarvis.WakeWordGate;
public final class WakeWordGateTest{
 private static int p=0,f=0;private static void ok(String n,boolean x){if(x){System.out.println("PASS "+n);p++;}else{System.out.println("FAIL "+n);f++;}}
 public static void main(String[] a){WakeWordGate g=new WakeWordGate(.32f,.50f,5,2,3500L);ok("single sub-threshold rejected",!g.accept(.29f,10000));ok("two moderate hey-jarvis peaks accepted",!g.accept(.36f,10080)&&g.accept(.41f,10160));ok("debounce blocks immediate retrigger",!g.accept(.80f,11000));ok("strong hey-jarvis peak accepted after debounce",g.accept(.62f,13661));g.reset();ok("speech-like low noise rejected",!g.accept(.10f,20000)&&!g.accept(.22f,20080)&&!g.accept(.30f,20160));ok("moderate separated votes accepted",!g.accept(.35f,20240)&&!g.accept(.18f,20320)&&g.accept(.38f,20400));System.out.println("TOTAL "+(p+f)+" PASS "+p+" FAIL "+f);if(f!=0)System.exit(1);}
}
