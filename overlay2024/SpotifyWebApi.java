package com.hakan.jarvis;

import android.content.Context;
import org.json.*;

import java.io.*;
import java.net.*;
import java.text.Normalizer;
import java.util.*;

public final class SpotifyWebApi {
    public static final String PROFILE="SPOTIFY_WEB_API_V1";

    public static final class AuthRequiredException extends Exception{
        AuthRequiredException(){super("Spotify OAuth required");}
    }

    public static final class Track{
        public final String id,uri,name,artist;
        public final int score;
        Track(String id,String uri,String name,String artist,int score){
            this.id=id;this.uri=uri;this.name=name;this.artist=artist;this.score=score;
        }
    }

    public static final class PlayResult{
        public final boolean success;
        public final boolean noDevice;
        public final Track track;
        public final int httpCode;
        PlayResult(boolean success,boolean noDevice,Track track,int httpCode){
            this.success=success;this.noDevice=noDevice;this.track=track;this.httpCode=httpCode;
        }
    }

    static final class Response{
        final int code;final String body;
        Response(int code,String body){this.code=code;this.body=body;}
    }

    static final class Device{
        String id,name,type;boolean active,restricted;
    }

    private SpotifyWebApi(){}

    public static Track searchExact(Context c,String artist,String title,String rawQuery)throws Exception{
        String query;
        if(valid(artist)&&valid(title))query="track:"+title+" artist:"+artist;
        else query=rawQuery==null?"":rawQuery.trim();
        if(query.length()<2)return null;

        Response r=request(c,"GET","https://api.spotify.com/v1/search?q="+enc(query)+"&type=track&limit=10",null,true);
        if(r.code!=200)throw new IOException("Spotify search HTTP "+r.code);
        return selectTrack(r.body,artist,title,rawQuery);
    }

    static Track selectTrack(String json,String artist,String title,String rawQuery)throws Exception{
        JSONObject root=new JSONObject(json);
        JSONObject tracks=root.optJSONObject("tracks");
        JSONArray items=tracks==null?null:tracks.optJSONArray("items");
        if(items==null||items.length()==0)return null;

        Track best=null;
        for(int i=0;i<items.length();i++){
            JSONObject t=items.optJSONObject(i);
            if(t==null)continue;
            String id=t.optString("id","");
            String uri=t.optString("uri","");
            String name=t.optString("name","");
            String ar=artistNames(t.optJSONArray("artists"));
            if(id.length()==0||uri.length()==0||name.length()==0)continue;
            int score=score(artist,title,rawQuery,ar,name);
            Track candidate=new Track(id,uri,name,ar,score);
            if(best==null||candidate.score>best.score)best=candidate;
        }
        if(best==null)return null;
        if(valid(artist)&&valid(title)&&best.score<140)return null;
        if(!valid(artist)&&!valid(title)&&best.score<15)return null;
        return best;
    }

    static int score(String wantedArtist,String wantedTitle,String raw,String actualArtist,String actualTitle){
        String wa=n(wantedArtist),wt=n(wantedTitle),aa=n(actualArtist),at=n(actualTitle);
        int s=0;
        if(wt.length()>0){
            if(at.equals(wt))s+=100;
            else if(at.contains(wt)||wt.contains(at))s+=65;
            else s+=tokenScore(wt,at,45);
        }
        if(wa.length()>0){
            if(aa.equals(wa))s+=100;
            else if(aa.contains(wa)||wa.contains(aa))s+=65;
            else s+=tokenScore(wa,aa,45);
        }
        if(wt.length()==0&&wa.length()==0){
            s+=tokenScore(n(raw),aa+" "+at,100);
        }else{
            s+=tokenScore(n(raw),aa+" "+at,20);
        }
        return s;
    }

    public static PlayResult playExact(Context c,String artist,String title,String rawQuery)throws Exception{
        Track track=searchExact(c,artist,title,rawQuery);
        if(track==null)return new PlayResult(false,false,null,404);

        Device d=chooseDevice(c);
        if(d==null)return new PlayResult(false,true,track,404);

        if(!d.active){
            JSONObject transfer=new JSONObject();
            JSONArray ids=new JSONArray();ids.put(d.id);
            transfer.put("device_ids",ids);transfer.put("play",false);
            Response tr=request(c,"PUT","https://api.spotify.com/v1/me/player",transfer.toString(),true);
            if(tr.code!=204&&tr.code!=200)return new PlayResult(false,false,track,tr.code);
        }

        JSONObject body=new JSONObject();
        JSONArray uris=new JSONArray();uris.put(track.uri);
        body.put("uris",uris);
        String url="https://api.spotify.com/v1/me/player/play?device_id="+enc(d.id);
        Response pr=request(c,"PUT",url,body.toString(),true);
        return new PlayResult(pr.code==204,false,track,pr.code);
    }

    public static boolean control(Context c,String action)throws Exception{
        String method,url;String body=null;
        if("PAUSE".equals(action)){method="PUT";url="https://api.spotify.com/v1/me/player/pause";}
        else if("RESUME".equals(action)){method="PUT";url="https://api.spotify.com/v1/me/player/play";body="{}";}
        else if("NEXT".equals(action)){method="POST";url="https://api.spotify.com/v1/me/player/next";}
        else if("PREVIOUS".equals(action)){method="POST";url="https://api.spotify.com/v1/me/player/previous";}
        else return false;
        Response r=request(c,method,url,body,true);
        return r.code==204||r.code==200;
    }

    static Device chooseDevice(Context c)throws Exception{
        Response r=request(c,"GET","https://api.spotify.com/v1/me/player/devices",null,true);
        if(r.code!=200)return null;
        JSONObject root=new JSONObject(r.body);
        JSONArray a=root.optJSONArray("devices");
        if(a==null)return null;
        Device active=null,phone=null,any=null;
        for(int i=0;i<a.length();i++){
            JSONObject x=a.optJSONObject(i);if(x==null)continue;
            Device d=new Device();
            d.id=x.optString("id","");
            d.name=x.optString("name","");
            d.type=x.optString("type","");
            d.active=x.optBoolean("is_active",false);
            d.restricted=x.optBoolean("is_restricted",false);
            if(d.id.length()==0||d.restricted)continue;
            if(d.active&&active==null)active=d;
            if("smartphone".equalsIgnoreCase(d.type)&&phone==null)phone=d;
            if(any==null)any=d;
        }
        return active!=null?active:(phone!=null?phone:any);
    }

    static Response request(Context c,String method,String url,String body,boolean retry)throws Exception{
        String token=SpotifyOAuthManager.getValidAccessToken(c);
        if(token==null||token.length()==0)throw new AuthRequiredException();

        HttpURLConnection h=(HttpURLConnection)new URL(url).openConnection();
        h.setConnectTimeout(6500);h.setReadTimeout(9000);
        h.setRequestMethod(method);
        h.setRequestProperty("Authorization","Bearer "+token);
        h.setRequestProperty("Accept","application/json");
        if(body!=null){
            h.setDoOutput(true);
            h.setRequestProperty("Content-Type","application/json");
            OutputStream out=h.getOutputStream();
            out.write(body.getBytes("UTF-8"));out.close();
        }
        int code=h.getResponseCode();
        String raw=read(code>=200&&code<300?h.getInputStream():h.getErrorStream(),500000);
        h.disconnect();

        if(code==401&&retry){
            SpotifyOAuthManager.invalidateAccess(c);
            return request(c,method,url,body,false);
        }
        return new Response(code,raw);
    }

    static String artistNames(JSONArray a){
        if(a==null)return "";
        StringBuilder b=new StringBuilder();
        for(int i=0;i<a.length();i++){
            JSONObject x=a.optJSONObject(i);if(x==null)continue;
            String name=x.optString("name","");
            if(name.length()>0){if(b.length()>0)b.append(", ");b.append(name);}
        }
        return b.toString();
    }

    static int tokenScore(String a,String b,int max){
        Set<String> aa=tokens(a),bb=tokens(b);
        if(aa.isEmpty()||bb.isEmpty())return 0;
        int hit=0;for(String x:aa)if(bb.contains(x))hit++;
        return (int)Math.round(max*(hit/(double)aa.size()));
    }

    static Set<String> tokens(String s){
        LinkedHashSet<String> out=new LinkedHashSet<String>();
        for(String x:n(s).split(" "))if(x.length()>1)out.add(x);
        return out;
    }

    static String n(String s){
        if(s==null)return "";
        String x=s.toLowerCase(new Locale("tr","TR"));
        x=x.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        x=Normalizer.normalize(x,Normalizer.Form.NFD).replaceAll("\\p{M}+","");
        return x.replaceAll("[^a-z0-9 ]+"," ").replaceAll("\\s+"," ").trim();
    }

    static boolean valid(String s){return s!=null&&s.trim().length()>=2;}
    static String enc(String s)throws Exception{return URLEncoder.encode(s==null?"":s,"UTF-8");}

    static String read(InputStream in,int max)throws Exception{
        if(in==null)return "";
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        byte[] buf=new byte[4096];int n,total=0;
        while((n=in.read(buf))!=-1){total+=n;if(total>max)throw new IOException("Response too large");out.write(buf,0,n);}
        in.close();return out.toString("UTF-8");
    }
}
