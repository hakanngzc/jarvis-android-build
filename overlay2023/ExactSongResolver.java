package com.hakan.jarvis;

import org.json.*;
import java.io.*;
import java.net.*;
import java.text.Normalizer;
import java.util.*;

public final class ExactSongResolver {
    public static final String PROFILE="EXACT_SONG_RESOLVER_V1";

    public interface Transport { String get(String url) throws Exception; }

    public static final class Result {
        public final String artist,title,query;
        public final int score;
        public final boolean resolved;
        Result(String artist,String title,int score,boolean resolved){
            this.artist=artist==null?"":artist.trim();
            this.title=title==null?"":title.trim();
            this.score=score;
            this.resolved=resolved;
            this.query=(this.artist+" "+this.title).trim();
        }
    }

    private ExactSongResolver(){}

    public static Result resolve(MediaCommandRouter.Command c,Transport t) throws Exception {
        if(c==null)return new Result("","",0,false);
        String artist=c.artist==null?"":c.artist.trim();
        String title=c.title==null?"":c.title.trim();

        // Explicit Turkish entity forms are already trustworthy.
        if(artist.length()>=2&&title.length()>=2)
            return new Result(artist,title,100,true);

        String raw=c.query==null?"":c.query.trim();
        if(raw.length()<2)return new Result(artist,title,0,false);

        String url="https://musicbrainz.org/ws/2/recording/?query="+enc(raw)+"&limit=8&fmt=json";
        JSONObject root=new JSONObject(t.get(url));
        JSONArray arr=root.optJSONArray("recordings");
        if(arr==null||arr.length()==0)return new Result("","",0,false);

        Candidate best=null;
        for(int i=0;i<arr.length();i++){
            JSONObject r=arr.optJSONObject(i);
            if(r==null)continue;
            String rt=clean(r.optString("title"));
            String ra=artistCredit(r.optJSONArray("artist-credit"));
            int api=r.optInt("score",0);
            if(rt.length()<1||ra.length()<1)continue;

            int lexical=similarity(raw,ra+" "+rt);
            int titleMatch=containsAll(raw,rt)?8:0;
            int artistMatch=containsAll(raw,ra)?8:0;
            int total=api+lexical+titleMatch+artistMatch;
            if(best==null||total>best.total)best=new Candidate(ra,rt,api,total);
        }
        if(best==null)return new Result("","",0,false);
        // MusicBrainz score is 0..100. Be conservative on weak fuzzy matches.
        if(best.api<55&&best.total<90)return new Result("","",best.api,false);
        return new Result(best.artist,best.title,best.api,true);
    }

    static final class Candidate{
        final String artist,title; final int api,total;
        Candidate(String a,String t,int api,int total){artist=a;title=t;this.api=api;this.total=total;}
    }

    static String artistCredit(JSONArray a){
        if(a==null)return "";
        StringBuilder b=new StringBuilder();
        for(int i=0;i<a.length();i++){
            JSONObject x=a.optJSONObject(i);
            if(x==null)continue;
            String n=clean(x.optString("name"));
            if(n.length()==0){
                JSONObject ar=x.optJSONObject("artist");
                if(ar!=null)n=clean(ar.optString("name"));
            }
            if(n.length()>0){
                if(b.length()>0)b.append(' ');
                b.append(n);
            }
        }
        return b.toString().trim();
    }

    static int similarity(String a,String b){
        Set<String> aa=tokens(a),bb=tokens(b);
        if(aa.isEmpty()||bb.isEmpty())return 0;
        int hit=0;
        for(String x:aa)if(bb.contains(x))hit++;
        return (int)Math.round(30.0*hit/Math.max(aa.size(),bb.size()));
    }

    static boolean containsAll(String raw,String part){
        Set<String> r=tokens(raw),p=tokens(part);
        return !p.isEmpty()&&r.containsAll(p);
    }

    static Set<String> tokens(String raw){
        String n=normalize(raw);
        LinkedHashSet<String>s=new LinkedHashSet<String>();
        for(String x:n.split(" "))if(x.length()>1)s.add(x);
        return s;
    }

    static String normalize(String raw){
        if(raw==null)return "";
        String s=raw.toLowerCase(new Locale("tr","TR"));
        s=s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s=Normalizer.normalize(s,Normalizer.Form.NFD).replaceAll("\\p{M}+","");
        return s.replaceAll("[^a-z0-9 ]+"," ").replaceAll("\\s+"," ").trim();
    }

    static String clean(String s){return s==null?"":s.replaceAll("\\s+"," ").trim();}
    static String enc(String s)throws Exception{return URLEncoder.encode(s,"UTF-8");}

    public static final class HttpsTransport implements Transport {
        private volatile HttpURLConnection active;
        private static long lastAt=0L;

        public void cancel(){HttpURLConnection c=active;if(c!=null)c.disconnect();}

        public String get(String address)throws Exception{
            URL u=new URL(address);
            if(!"https".equals(u.getProtocol())||!"musicbrainz.org".equals(u.getHost()))
                throw new IOException("Untrusted music resolver endpoint");

            synchronized(HttpsTransport.class){
                long now=System.currentTimeMillis();
                long wait=1000L-(now-lastAt);
                if(wait>0)Thread.sleep(wait);
                lastAt=System.currentTimeMillis();
            }

            HttpURLConnection c=(HttpURLConnection)u.openConnection();
            active=c;
            c.setConnectTimeout(4500);
            c.setReadTimeout(6500);
            c.setInstanceFollowRedirects(false);
            c.setRequestProperty("Accept","application/json");
            c.setRequestProperty("User-Agent","JARVIS-Android/2.0.2.3 (personal non-commercial assistant)");
            try{
                int code=c.getResponseCode();
                if(code!=200)throw new IOException("MusicBrainz HTTP "+code);
                InputStream in=c.getInputStream();
                try{return read(in,400000);}finally{in.close();}
            }finally{
                c.disconnect();
                if(active==c)active=null;
            }
        }
    }

    static String read(InputStream in,int max)throws Exception{
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        byte[] buf=new byte[4096];int n,total=0;
        while((n=in.read(buf))!=-1){
            total+=n;if(total>max)throw new IOException("Response too large");
            out.write(buf,0,n);
        }
        return out.toString("UTF-8");
    }
}
