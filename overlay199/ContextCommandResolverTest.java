package com.hakan.jarvis;

public final class ContextCommandResolverTest {
    private static int pass=0, fail=0;

    private static void expect(String input,String prev,long age,String expected){
        ContextCommandResolver.Resolution r=ContextCommandResolver.resolve(input,prev,age);
        String got=r==null?null:r.resolvedCommand;
        if(expected==null?got==null:expected.equals(got)) pass++;
        else {
            fail++;
            System.out.println("FAIL input="+input+" prev="+prev+" expected="+expected+" got="+got);
        }
    }

    private static void track(String input,boolean expected){
        boolean got=ContextCommandResolver.isTrackable(input);
        if(got==expected)pass++;
        else{fail++;System.out.println("FAIL track "+input+" expected="+expected+" got="+got);}
    }

    public static void main(String[] args){
        expect("biraz daha","sesi yükselt",5000,"sesi yükselt");
        expect("bir tık daha","Jarvis sesi yükselt",5000,"sesi yükselt");
        expect("geri al","sesi yükselt",5000,"sesi kıs");
        expect("biraz daha","sesi kıs",5000,"sesi kıs");
        expect("tersini yap","sesi kıs",5000,"sesi yükselt");

        expect("kapat","feneri aç",5000,"feneri kapat");
        expect("geri aç","feneri kapat",5000,"feneri aç");
        expect("tekrar yap","feneri aç",5000,"feneri aç");

        expect("tekrar aç","Spotify aç",5000,"Spotify aç");
        expect("yeniden aç","YouTube'u aç",5000,"YouTube aç");
        expect("kapat","Spotify aç",5000,null);

        expect("5 dakika daha ekle","20 dakika sonra alarm kur",5000,"25 dakika sonra alarm kur");
        expect("10 dakika azalt","20 dakika sonra alarm kur",5000,"10 dakika sonra alarm kur");
        expect("30 dakika uzat","45 dakika sonra alarm kur",5000,"75 dakika sonra alarm kur");
        expect("tekrar kur","15 dakika sonra alarm kur",5000,"15 dakika sonra alarm kur");
        expect("30 dakika azalt","20 dakika sonra alarm kur",5000,null);

        expect("biraz daha","sesi yükselt",91000,null);
        expect("kapat","feneri aç",120000,null);
        expect("biraz daha","",5000,null);

        track("Jarvis feneri aç",true);
        track("sesi yükselt",true);
        track("Spotify aç",true);
        track("20 dakika sonra alarm kur",true);
        track("annemi ara",false);
        track("mesaj gönder",false);
        track("merhaba",false);

        System.out.println("ContextCommandResolver: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
