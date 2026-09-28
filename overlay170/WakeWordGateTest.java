import com.hakan.jarvis.WakeWordGate;
public final class WakeWordGateTest{
 private static int p=0,f=0;private static void ok(String n,boolean x){if(x){System.out.println("PASS "+n);p++;}else{System.out.println("FAIL "+n);f++;}}
 public static void main(String[] a){
  WakeWordGate g=new WakeWordGate(.30f,.48f,5,2,3800L);
  ok("one moderate frame rejected",!g.accept(.34f,10000));
  ok("second moderate frame accepted",g.accept(.37f,10080));
  ok("debounce blocks immediate retrigger",!g.accept(.80f,12000));
  ok("single strong 69 percent peak accepted",g.accept(.69f,13881));
  g.reset();
  ok("sub-threshold background rejected",!g.accept(.10f,20000)&&!g.accept(.22f,20080)&&!g.accept(.29f,20160));
  ok("single 47 percent near miss rejected",!g.accept(.47f,21000));
  ok("single 48 percent strong accepted",g.accept(.48f,25000));
  System.out.println("TOTAL "+(p+f)+" PASS "+p+" FAIL "+f);if(f!=0)System.exit(1);
 }
}
