import com.hakan.jarvis.WakeWordGate;
public final class WakeWordGateTest{
 private static int p=0,f=0;private static void ok(String n,boolean x){if(x){System.out.println("PASS "+n);p++;}else{System.out.println("FAIL "+n);f++;}}
 public static void main(String[] a){
  WakeWordGate g=new WakeWordGate(.30f,.55f,6,3,3800L);
  ok("one moderate frame rejected",!g.accept(.36f,10000));
  ok("two moderate frames rejected",!g.accept(.38f,10080));
  ok("third moderate hey-jarvis frame accepted",g.accept(.40f,10160));
  ok("debounce blocks immediate retrigger",!g.accept(.80f,12000));
  ok("strong peak accepted after debounce",g.accept(.61f,14001));
  g.reset();
  ok("background sequence rejected",!g.accept(.10f,20000)&&!g.accept(.18f,20080)&&!g.accept(.26f,20160)&&!g.accept(.29f,20240));
  System.out.println("TOTAL "+(p+f)+" PASS "+p+" FAIL "+f);if(f!=0)System.exit(1);
 }
}
