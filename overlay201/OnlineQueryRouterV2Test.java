package com.hakan.jarvis;

public final class OnlineQueryRouterV2Test {
    static int pass=0,fail=0;
    static void e(String q,boolean x){
        boolean g=OnlineQueryRouter.shouldHandle(q);
        if(g==x)pass++;else{fail++;System.out.println("FAIL "+q+" expected="+x+" got="+g);}
    }
    public static void main(String[]a){
        e("Kara delikleri bana anlat",true);
        e("Kara delikleri açıkla",true);
        e("GPS ne işe yarar",true);
        e("DNA neden önemli",true);
        e("Motor nasıl çalışıyor",true);
        e("RAM ile depolama arasındaki fark ne",true);
        e("Fotosentezi anlatabilir misin",true);
        e("Yer çekimini açıklayabilir misin",true);

        e("biraz daha anlat",false);
        e("devam et",false);
        e("kaynağın ne",false);
        e("kaynağı aç",false);
        e("tekrar söyle",false);
        e("kısaca anlat",false);

        e("feneri aç",false);
        e("annemi ara",false);
        e("20 dakika sonra alarm kur",false);
        e("yarın hava nasıl",false);
        System.out.println("OnlineQueryRouterV2: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
