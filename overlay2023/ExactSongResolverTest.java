package com.hakan.jarvis;

public final class ExactSongResolverTest {
    static int pass=0,fail=0;
    static void ok(boolean v,String name){if(v)pass++;else{fail++;System.out.println("FAIL "+name);}}
    public static void main(String[]a)throws Exception{
        MediaCommandRouter.Command explicit=MediaCommandRouter.parse("Spotify'da Nilüfer'i Müslüm'den aç","",0);
        ExactSongResolver.Result e=ExactSongResolver.resolve(explicit,new ExactSongResolver.Transport(){public String get(String u){throw new RuntimeException("network should not run");}});
        ok(e.resolved&&"Müslüm".equals(e.artist)&&"Nilüfer".equals(e.title),"explicit entity");

        MediaCommandRouter.Command flat=MediaCommandRouter.parse("Müslüm Gürses Nilüfer çal","",0);
        final String json="{\"recordings\":[{\"score\":100,\"title\":\"Nilüfer\",\"artist-credit\":[{\"name\":\"Müslüm Gürses\"}]},{\"score\":72,\"title\":\"Nilüfer\",\"artist-credit\":[{\"name\":\"Başka Sanatçı\"}]}]}";
        ExactSongResolver.Result r=ExactSongResolver.resolve(flat,new ExactSongResolver.Transport(){public String get(String u){return json;}});
        ok(r.resolved,"flat resolved");
        ok("Müslüm Gürses".equals(r.artist),"artist");
        ok("Nilüfer".equals(r.title),"title");
        ok("Müslüm Gürses Nilüfer".equals(r.query),"canonical query");

        final String weak="{\"recordings\":[{\"score\":20,\"title\":\"Alakasız\",\"artist-credit\":[{\"name\":\"Başka\"}]}]}";
        ExactSongResolver.Result w=ExactSongResolver.resolve(flat,new ExactSongResolver.Transport(){public String get(String u){return weak;}});
        ok(!w.resolved,"weak rejected");

        System.out.println("ExactSongResolver: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
