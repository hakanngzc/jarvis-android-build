package com.hakan.jarvis;

public final class OnlineFollowupRouterTest {
    static int pass=0,fail=0;
    static String body(){
        StringBuilder b=new StringBuilder();
        for(int i=0;i<18;i++)b.append("Bu bilgi cümlesi ").append(i+1).append(" ve konu hakkında açıklama içerir. ");
        return b.toString();
    }
    static void kind(String q,long age,String expected){
        OnlineFollowupRouter.Followup f=OnlineFollowupRouter.match(
            q,"Deneme Başlığı",body(),"Türkçe Wikipedia · en ilgili eşleşme",
            "https://tr.wikipedia.org/wiki/Deneme",age);
        String g=f==null?null:f.kind;
        if(expected==null?g==null:expected.equals(g))pass++;
        else{fail++;System.out.println("FAIL "+q+" expected="+expected+" got="+g);}
    }
    public static void main(String[]a){
        kind("biraz daha anlat",1000,"more");
        kind("devam et",1000,"more");
        kind("kısaca söyle",1000,"short");
        kind("özetle",1000,"short");
        kind("tekrar söyle",1000,"repeat");
        kind("kaynağın ne",1000,"source");
        kind("nereden biliyorsun",1000,"source");
        kind("kaynağı aç",1000,"open_source");
        kind("biraz daha anlat",181000,null);
        kind("merhaba",1000,null);

        String shortText=OnlineFollowupRouter.shortText(body());
        if(shortText.length()>0&&shortText.length()<=330)pass++;else{fail++;System.out.println("FAIL short len="+shortText.length());}
        String more=OnlineFollowupRouter.moreText(body());
        if(more.length()>0&&!more.equals("Elimdeki çevrimiçi özet bu kadar efendim."))pass++;else{fail++;System.out.println("FAIL more");}
        String repeat=OnlineFollowupRouter.repeatText("Deneme Başlığı",body());
        if(repeat.startsWith("Deneme Başlığı."))pass++;else{fail++;System.out.println("FAIL repeat");}

        System.out.println("OnlineFollowupRouter: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
