package com.hakan.jarvis;

public final class MediaCommandRouterTest {
    static int pass=0,fail=0;

    static void expect(String raw,String last,long age,String action,String provider,String query,String artist,String title){
        MediaCommandRouter.Command c=MediaCommandRouter.parse(raw,last,age);
        boolean ok=c!=null&&action.equals(c.action)&&provider.equals(c.provider)
            &&query.equals(c.query)&&artist.equals(c.artist)&&title.equals(c.title);
        if(ok)pass++;else{
            fail++;
            System.out.println("FAIL "+raw+" got="+(c==null?"null":c.action+"|"+c.provider+"|"+c.query+"|"+c.artist+"|"+c.title));
        }
    }
    static void none(String raw,String last,long age){
        MediaCommandRouter.Command c=MediaCommandRouter.parse(raw,last,age);
        if(c==null)pass++;else{fail++;System.out.println("FAIL expected null "+raw+" got="+c.action);}
    }

    public static void main(String[]a){
        expect("Spotify aç","",0,"OPEN","spotify","","","");
        expect("YouTube'u aç","",0,"OPEN","youtube","","","");
        expect("YouTube Music aç","",0,"OPEN","youtube_music","","","");

        expect("Spotify'da Müslüm Gürses Nilüfer çal","",0,"PLAY","spotify","Müslüm Gürses Nilüfer","","");
        expect("Müslüm Gürses Nilüfer çal","",0,"PLAY","spotify","Müslüm Gürses Nilüfer","","");
        expect("Tarkan Kuzu Kuzu çal","",0,"PLAY","spotify","Tarkan Kuzu Kuzu","","");
        expect("YouTube'dan Barış Manço Gülpembe aç","",0,"PLAY","youtube","Barış Manço Gülpembe","","");
        expect("YouTube Music'ten Sezen Aksu Gülümse çal","",0,"PLAY","youtube_music","Sezen Aksu Gülümse","","");

        expect("Spotify'da Nilüfer'i Müslüm'den aç","",0,"PLAY","spotify","Müslüm Nilüfer","Müslüm","Nilüfer");
        expect("Spotify'da Sezen'den bir şey aç","",0,"PLAY","spotify","Sezen","Sezen","");
        expect("Spotify'da Müslüm'den Nilüfer çal","",0,"PLAY","spotify","Müslüm Nilüfer","Müslüm","Nilüfer");

        expect("YouTube'da Müslüm Gürses ara","",0,"SEARCH","youtube","Müslüm Gürses","","");
        expect("Spotify'da Tarkan ara","",0,"SEARCH","spotify","Tarkan","","");

        expect("durdur","spotify",5000,"PAUSE","spotify","","","");
        expect("şarkıyı durdur","youtube",5000,"PAUSE","youtube","","","");
        expect("Spotify'ı kapat","youtube",5000,"PAUSE","spotify","","","");
        expect("devam et","spotify",5000,"RESUME","spotify","","","");
        expect("sonraki","spotify",5000,"NEXT","spotify","","","");
        expect("önceki şarkı","youtube_music",5000,"PREVIOUS","youtube_music","","","");

        none("devam et","spotify",MediaCommandRouter.CONTEXT_WINDOW_MS+1);
        none("sonraki","",0);
        none("merhaba","spotify",5000);
        none("20 dakika sonra alarm kur","spotify",5000);
        none("feneri aç","spotify",5000);

        expect("Hey Jarvis Spotify'da Tarkan Kuzu Kuzu çal","",0,"PLAY","spotify","Tarkan Kuzu Kuzu","","");
        expect("Jarvis YouTube'da Barış Manço ara","",0,"SEARCH","youtube","Barış Manço","","");

        System.out.println("MediaCommandRouter: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
