import com.hakan.jarvis.WakeWordGate;
public final class WakeWordGateTest{
 private static int p=0,f=0;private static void ok(String n,boolean x){if(x){System.out.println("PASS "+n);p++;}else{System.out.println("FAIL "+n);f++;}}
 public static void main(String[] a){WakeWordGate g=new WakeWordGate(.22f,.45f,5,2,3500L);ok("single low score rejected",!g.accept(.23f,10000));ok("two Turkish-accent moderate peaks accepted",!g.accept(.27f,10080)&&g.accept(.29f,10160));ok("debounce blocks immediate retrigger",!g.accept(.75f,11000));ok("strong hey-jarvis peak accepted after debounce",g.accept(.52f,13661));g.reset();ok("low background sequence rejected",!g.accept(.06f,20000)&&!g.accept(.15f,20080)&&!g.accept(.21f,20160));ok("moderate separated votes accepted",!g.accept(.25f,20240)&&!g.accept(.11f,20320)&&g.accept(.26f,20400));System.out.println("TOTAL "+(p+f)+" PASS "+p+" FAIL "+f);if(f!=0)System.exit(1);}
}
