package com.hakan.jarvis;

import android.app.Activity;
import android.content.*;
import android.net.Uri;
import java.io.*;
import java.net.*;
import java.text.Normalizer;
import java.util.*;

public final class SpotifyWebApi {
    public static final String PROFILE="SPOTIFY_WEB_API_V1";

    private SpotifyWebApi(){}

    public static void execute(Activity a,MediaCommandRouter.Command c)throws Exception{
        if(c==null)return;
        if("PLAY".equals(c.action)){playExact(a,c);return;}
        if("PAUSE".equals(c.action)){request(a,"PUT","https://api.spotify.com/v1/me/player/pause","",204);return;}
        if("RESUME".equals(c.action)){request(a,"PUT","https://api.spotify.com/v1/me/player/play","{}",204);return;}
        if("NEXT".equals(c.action)){request(a,"POST","https://api.spotify.com/v1/me/player/next","",204);return;}
        if("PREVIOUS".equals(c.action)){request(a,"POST","https://api.spotify.com/v1/me/player/previous","",204);return;}
    }

    public static void executeFromContext(Context c,MediaCommandRouter.Command cmd){
        if(!(c instanceof Activity)){
            Intent launch=c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
            if(launch!=null){launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);c.startActivity(launch);}
            return;
        }
        final Activity a=(Activity)c;
        new Thread(new Runnable(){public void run(){
            try{execute(a,cmd);}
            catch(Exception e){a.runOnUiThread(new Runnable(){public void run(){MediaActions.executeLegacy(a,cmd);}});}
        }},"jarvis-spotify-after-oauth").start();
    }

    static void playExact(Activity a,MediaCommandRouter.Command c)throws Exception{
        Track t=searchBest(a,c);
        if(t==null||t.uri.length()==0)throw new IOException("Spotify track not found");

        String body="{\"uris\":[\""+json(t.uri)+"\"]}";
        try{
            request(a,"PUT","https://api.spotify.com/v1/me/player/play",body,204);
            MediaActions.oauthStatus("Spotify: "+t.artist+" - "+t.title);
            return;
        }catch(HttpStatusException e){
            if(e.code!=404&&e.code!=403)throw e;
        }

        // No active Connect device or account/player limitation:
        // open the exact Spotify URI, then retry once.
        final String uri=t.uri;
        a.runOnUiThread(new Runnable(){public void run(){
            try{
                Intent i=new Intent(Intent.ACTION_VIEW,Uri.parse(uri)).setPackage("com.spotify.music");
                i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                a.startActivity(i);
            }catch(Exception ignored){}
        }});
        try{Thread.sleep(1400L);}catch(InterruptedException ignored){}
        request(a,"PUT","https://api.spotify.com/v1/me/player/play",body,204);
        MediaActions.oauthStatus("Spotify exact URI: "+t.artist+" - "+t.title);
    }

    static Track searchBest(Context c,MediaCommandRouter.Command cmd)throws Exception{
        String artist=clean(cmd.artist), title=clean(cmd.title), raw=clean(cmd.query);
        String q;
        if(artist.length()>0&&title.length()>0)q="track:"+title+" artist:"+artist;
        else q=raw;
        String url="https://api.spotify.com/v1/search?q="+URLEncoder.encode(q,"UTF-8")+"&type=track&limit=10";
        String json=request(c,"GET",url,"",200);
        Track best=selectBestTrack(json,artist,title,raw);
        if(best!=null)return best;

        if(!q.equals(raw)&&raw.length()>0){
            String url2="https://api.spotify.com/v1/search?q="+URLEncoder.encode(raw,"UTF-8")+"&type=track&limit=10";
            best=selectBestTrack(request(c,"GET",url2,"",200),artist,title,raw);
        }
        return best;
    }

    public static Track selectBestTrack(String json,String wantedArtist,String wantedTitle,String raw)throws Exception{
        org.json.JSONObject root=new org.json.JSONObject(json);
        org.json.JSONObject tracks=root.optJSONObject("tracks");
        org.json.JSONArray items=tracks==null?null:tracks.optJSONArray("items");
        if(items==null||items.length()==0)return null;

        Track best=null;int bestScore=-999;
        for(int i=0;i<items.length();i++){
            org.json.JSONObject x=items.optJSONObject(i);
            if(x==null)continue;
            String title=clean(x.optString("name",""));
            String uri=clean(x.optString("uri",""));
            org.json.JSONArray aa=x.optJSONArray("artists");
            String artist="";
            if(aa!=null&&aa.length()>0){
                org.json.JSONObject ar=aa.optJSONObject(0);
                if(ar!=null)artist=clean(ar.optString("name",""));
            }
            if(title.length()==0||artist.length()==0||!uri.startsWith("spotify:track:"))continue;

            int score=0;
            if(wantedTitle.length()>0){
                if(norm(title).equals(norm(wantedTitle)))score+=80;
                else if(norm(title).contains(norm(wantedTitle))||norm(wantedTitle).contains(norm(title)))score+=45;
                else score-=25;
            }
            if(wantedArtist.length()>0){
                if(norm(artist).equals(norm(wantedArtist)))score+=80;
                else if(norm(artist).contains(norm(wantedArtist))||norm(wantedArtist).contains(norm(artist)))score+=45;
                else score-=30;
            }
            if(raw.length()>0){
                Set<String> rt=tokens(raw), ct=tokens(artist+" "+title);
                int hits=0;for(String z:rt)if(ct.contains(z))hits++;
                score+=hits*8;
            }
            if(score>bestScore){bestScore=score;best=new Track(artist,title,uri,x.optString("id",""),score);}
        }
        if(best==null)return null;
        if((wantedArtist.length()>0||wantedTitle.length()>0)&&best.score<70)return null;
        return best;
    }

    static String request(Context c,String method,String url,String body,int expected)throws Exception{
        return request(c,method,url,body,expected,false);
    }

    static String request(Context c,String method,String url,String body,int expected,boolean retried)throws Exception{
        if(!SpotifyOAuthManager.ensureFreshToken(c))throw new IOException("Spotify auth required");
        String token=SpotifyOAuthManager.accessToken(c);
        HttpURLConnection h=(HttpURLConnection)new URL(url).openConnection();
        h.setConnectTimeout(7000);h.setReadTimeout(10000);
        h.setRequestMethod(method);
        h.setRequestProperty("Authorization","Bearer "+token);
        h.setRequestProperty("Accept","application/json");
        if("PUT".equals(method)||"POST".equals(method)){
            h.setDoOutput(true);
            h.setRequestProperty("Content-Type","application/json");
            if(body==null)body="";
            byte[] b=body.getBytes("UTF-8");
            h.getOutputStream().write(b);
        }
        int code=h.getResponseCode();
        InputStream in=code>=200&&code<300?h.getInputStream():h.getErrorStream();
        String out=read(in,500000);
        h.disconnect();
        if(code==expected)return out;
        if(code==401&&!retried){
            SpotifyOAuthManager.invalidateAccessToken(c);
            if(SpotifyOAuthManager.ensureFreshToken(c))
                return request(c,method,url,body,expected,true);
        }
        throw new HttpStatusException(code,out);
    }

    public static final class Track{
        public final String artist,title,uri,id;public final int score;
        Track(String a,String t,String u,String i,int s){artist=a;title=t;uri=u;id=i;score=s;}
    }

    public static final class HttpStatusException extends IOException{
        public final int code;public final String body;
        HttpStatusException(int c,String b){super("Spotify HTTP "+c);code=c;body=b;}
    }

    static String json(String s){return s.replace("\\","\\\\").replace("\"","\\\"");}
    static String clean(String s){return s==null?"":s.replaceAll("\\s+"," ").trim();}
    static String norm(String s){
        s=clean(s).toLowerCase(new Locale("tr","TR"));
        s=s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s=Normalizer.normalize(s,Normalizer.Form.NFD).replaceAll("\\p{M}+","");
        return s.replaceAll("[^a-z0-9 ]+"," ").replaceAll("\\s+"," ").trim();
    }
    static Set<String> tokens(String s){
        LinkedHashSet<String> o=new LinkedHashSet<String>();
        for(String x:norm(s).split(" "))if(x.length()>1)o.add(x);
        return o;
    }
    static String read(InputStream in,int max)throws Exception{
        if(in==null)return "";
        ByteArrayOutputStream o=new ByteArrayOutputStream();byte[] b=new byte[4096];int n,total=0;
        while((n=in.read(b))!=-1){total+=n;if(total>max)throw new IOException("Response too large");o.write(b,0,n);}
        return o.toString("UTF-8");
    }
}
