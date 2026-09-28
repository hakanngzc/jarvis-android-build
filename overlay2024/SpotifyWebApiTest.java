package com.hakan.jarvis;

public final class SpotifyWebApiTest {
    static int pass=0,fail=0;
    static void ok(boolean v,String n){if(v)pass++;else{fail++;System.out.println("FAIL "+n);}}
    public static void main(String[]a)throws Exception{
        String json="{\"tracks\":{\"items\":["
          +"{\"id\":\"x1\",\"uri\":\"spotify:track:x1\",\"name\":\"Nilüfer\",\"artists\":[{\"name\":\"Başka Sanatçı\"}]},"
          +"{\"id\":\"x2\",\"uri\":\"spotify:track:x2\",\"name\":\"Nilüfer\",\"artists\":[{\"name\":\"Müslüm Gürses\"}]},"
          +"{\"id\":\"x3\",\"uri\":\"spotify:track:x3\",\"name\":\"Nilüfer Remix\",\"artists\":[{\"name\":\"Müslüm Gürses\"}]}"
          +"]}}";

        SpotifyWebApi.Track t=SpotifyWebApi.selectTrack(json,"Müslüm Gürses","Nilüfer","Müslüm Gürses Nilüfer");
        ok(t!=null,"track selected");
        ok("spotify:track:x2".equals(t.uri),"exact uri");
        ok("Müslüm Gürses".equals(t.artist),"artist");
        ok("Nilüfer".equals(t.name),"title");

        String flat="{\"tracks\":{\"items\":["
          +"{\"id\":\"a\",\"uri\":\"spotify:track:a\",\"name\":\"Kuzu Kuzu\",\"artists\":[{\"name\":\"Tarkan\"}]},"
          +"{\"id\":\"b\",\"uri\":\"spotify:track:b\",\"name\":\"Şımarık\",\"artists\":[{\"name\":\"Tarkan\"}]}"
          +"]}}";
        SpotifyWebApi.Track f=SpotifyWebApi.selectTrack(flat,"","","Tarkan Kuzu Kuzu");
        ok(f!=null&&"spotify:track:a".equals(f.uri),"flat query exact");

        ok(SpotifyOAuthManager.REDIRECT_URI.equals("http://127.0.0.1:43821/callback"),"loopback redirect");
        ok(SpotifyOAuthManager.SCOPES.contains("user-modify-playback-state"),"modify scope");
        ok(SpotifyOAuthManager.SCOPES.contains("user-read-playback-state"),"read scope");

        System.out.println("SpotifyWebApi: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
