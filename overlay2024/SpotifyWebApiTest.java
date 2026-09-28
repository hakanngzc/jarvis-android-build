package com.hakan.jarvis;

public final class SpotifyWebApiTest {
    static int pass=0,fail=0;
    static void ok(boolean v,String n){if(v)pass++;else{fail++;System.out.println("FAIL "+n);}}

    public static void main(String[]args)throws Exception{
        String json="{\"tracks\":{\"items\":["
          +"{\"id\":\"wrong1\",\"name\":\"Nilüfer\",\"uri\":\"spotify:track:wrong1\",\"artists\":[{\"name\":\"Başka Sanatçı\"}]},"
          +"{\"id\":\"right1\",\"name\":\"Nilüfer\",\"uri\":\"spotify:track:right1\",\"artists\":[{\"name\":\"Müslüm Gürses\"}]},"
          +"{\"id\":\"wrong2\",\"name\":\"Nilüfer Remix\",\"uri\":\"spotify:track:wrong2\",\"artists\":[{\"name\":\"Müslüm Gürses Tribute\"}]}"
          +"]}}";

        SpotifyWebApi.Track a=SpotifyWebApi.selectBestTrack(json,"Müslüm Gürses","Nilüfer","Müslüm Gürses Nilüfer");
        ok(a!=null,"exact result exists");
        ok("right1".equals(a.id),"exact id");
        ok("spotify:track:right1".equals(a.uri),"exact uri");
        ok("Müslüm Gürses".equals(a.artist),"exact artist");
        ok("Nilüfer".equals(a.title),"exact title");

        SpotifyWebApi.Track b=SpotifyWebApi.selectBestTrack(json,"Tarkan","Kuzu Kuzu","Tarkan Kuzu Kuzu");
        ok(b==null,"reject unrelated results");

        String json2="{\"tracks\":{\"items\":[{\"id\":\"tarkan1\",\"name\":\"Kuzu Kuzu\",\"uri\":\"spotify:track:tarkan1\",\"artists\":[{\"name\":\"Tarkan\"}]}]}}";
        SpotifyWebApi.Track c=SpotifyWebApi.selectBestTrack(json2,"Tarkan","Kuzu Kuzu","Tarkan Kuzu Kuzu");
        ok(c!=null&&"tarkan1".equals(c.id),"tarkan exact");

        ok("muslum gurses".equals(SpotifyWebApi.norm("Müslüm Gürses")),"turkish normalize");

        System.out.println("SpotifyWebApi: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
