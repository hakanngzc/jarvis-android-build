package com.hakan.jarvis;

public final class ContactCommandRouterTest {
    static int pass=0,fail=0;
    static void expect(String raw,String last,long age,String action,String target,String msg,String ch){
        ContactCommandRouter.Command c=ContactCommandRouter.parse(raw,last,age);
        boolean ok=c!=null&&action.equals(c.action)&&target.equals(c.target)&&msg.equals(c.message)&&ch.equals(c.channel);
        if(ok)pass++;else{fail++;System.out.println("FAIL "+raw+" -> "+(c==null?"null":c.action+"|"+c.target+"|"+c.message+"|"+c.channel));}
    }
    static void none(String raw){
        ContactCommandRouter.Command c=ContactCommandRouter.parse(raw,"",Long.MAX_VALUE);
        if(c==null)pass++;else{fail++;System.out.println("FAIL reject "+raw+" -> "+c.action);}
    }
    public static void main(String[]a){
        expect("Ahmet'i ara","",0,"CALL","ahmet","","call");
        expect("Biraderimi ara","",0,"CALL","biraderimi","","call");
        expect("Hey Jarvis annemi ara","",0,"CALL","annemi","","call");
        expect("İkbal'e WhatsApp'tan merhaba yaz","",0,"MESSAGE","ikbal","merhaba","whatsapp");
        expect("Ahmet'e WhatsApp'tan yaz","",0,"MESSAGE","ahmet","","whatsapp");
        expect("Ahmet'e mesaj gönder","",0,"MESSAGE","ahmet","","sms");
        expect("Ahmet'e mesaj gönder merhaba nasılsın","",0,"MESSAGE","ahmet","merhaba nasilsin","sms");
        expect("olmadı WhatsApp'tan yaz","Ahmet",1000,"MESSAGE","Ahmet","","whatsapp");
        expect("ona WhatsApp'tan merhaba yaz","İkbal",1000,"MESSAGE","İkbal","merhaba","whatsapp");
        expect("ona mesaj at nasılsın","İkbal",1000,"MESSAGE","İkbal","nasilsin","sms");
        expect("onu ara","Ahmet",1000,"CALL","Ahmet","","call");

        if(ContactCommandRouter.yes("evet"))pass++;else fail++;
        if(ContactCommandRouter.yes("onaylıyorum"))pass++;else fail++;
        if(ContactCommandRouter.no("iptal"))pass++;else fail++;
        if(ContactCommandRouter.no("gönderme"))pass++;else fail++;

        none("05551234567 ara");
        none("Bluetooth'u aç");
        none("20 dakika sonra alarm kur");
        none("Müslüm Gürses Nilüfer çal");

        System.out.println("ContactCommandRouter: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
