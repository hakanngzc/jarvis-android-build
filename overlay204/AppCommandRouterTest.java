package com.hakan.jarvis;

public final class AppCommandRouterTest {
    static int pass=0,fail=0;

    static void expect(String raw,String last,long age,String action,String target){
        AppCommandRouter.Command c=AppCommandRouter.parse(raw,last,age);
        boolean ok=c!=null&&action.equals(c.action)&&target.equals(c.target);
        if(ok)pass++;else{fail++;System.out.println("FAIL "+raw+" -> "+(c==null?"null":c.action+" "+c.target));}
    }

    static void reject(String raw){
        AppCommandRouter.Command c=AppCommandRouter.parse(raw,"",Long.MAX_VALUE);
        if(c==null)pass++;else{fail++;System.out.println("FAIL reject "+raw+" -> "+c.action+" "+c.target);}
    }

    public static void main(String[]args){
        expect("Instagram'ı aç","",0,"OPEN","instagram");
        expect("WhatsApp aç","",0,"OPEN","whatsapp");
        expect("Hey Jarvis kamerayı aç","",0,"OPEN","kamera");
        expect("ayarları aç","",0,"OPEN","ayarlar");
        expect("uygulama Telegram aç","",0,"OPEN","telegram");
        expect("başlat Chrome","",0,"OPEN","chrome");
        expect("Instagram'ı kapat","",0,"CLOSE","instagram");
        expect("onu aç","instagram",1000,"OPEN","instagram");
        expect("tekrar aç","whatsapp",1000,"OPEN","whatsapp");
        expect("onu kapat","telegram",1000,"CLOSE","telegram");

        reject("Bluetooth'u aç");
        reject("Wi-Fi'yi kapat");
        reject("feneri aç");
        reject("alarm kur");
        reject("Müslüm Gürses Nilüfer çal");
        reject("sesi yükselt");

        System.out.println("AppCommandRouter: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
