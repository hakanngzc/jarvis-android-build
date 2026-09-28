package com.hakan.jarvis;

import android.app.Activity;
import android.content.*;
import android.net.Uri;
import java.io.*;
import java.net.*;
import java.security.*;
import java.util.*;
import android.util.Base64;

public final class SpotifyOAuthManager {
    public static final String PROFILE="SPOTIFY_PKCE_OAUTH_V1";
    public static final String CLIENT_ID="e6a9bcc48fc34959aa5914e46efb1a44";
    public static final String REDIRECT_URI="http://127.0.0.1:43821/callback";
    public static final String SCOPES="user-modify-playback-state user-read-playback-state user-read-currently-playing";
    private static final String PREF="jarvis_spotify_oauth_v1";
    private static final int PORT=43821;
    private static volatile boolean callbackRunning=false;

    private SpotifyOAuthManager(){}

    public static boolean hasAccessToken(Context c){
        SharedPreferences p=c.getSharedPreferences(PREF,Context.MODE_PRIVATE);
        String token=p.getString("access_token","");
        long exp=p.getLong("expires_at",0L);
        return token.length()>20 && exp>System.currentTimeMillis()+60000L;
    }

    public static String accessToken(Context c){
        return c.getSharedPreferences(PREF,Context.MODE_PRIVATE).getString("access_token","");
    }

    public static boolean handle(Activity a,MediaCommandRouter.Command c){
        if(c==null||!"spotify".equals(c.provider))return false;
        if(!("PLAY".equals(c.action)||"PAUSE".equals(c.action)||"RESUME".equals(c.action)||"NEXT".equals(c.action)||"PREVIOUS".equals(c.action)))return false;

        rememberPending(a,c);
        new Thread(new Runnable(){public void run(){
            try{
                if(!ensureFreshToken(a)){
                    a.runOnUiThread(new Runnable(){public void run(){beginAuthorization(a);}});
                    return;
                }
                SpotifyWebApi.execute(a,c);
            }catch(Exception e){
                a.runOnUiThread(new Runnable(){public void run(){MediaActions.executeLegacy(a,c);}});
            }
        }},"jarvis-spotify-oauth").start();
        return true;
    }

    public static boolean ensureFreshToken(Context c)throws Exception{
        if(hasAccessToken(c))return true;
        SharedPreferences p=c.getSharedPreferences(PREF,Context.MODE_PRIVATE);
        String refresh=p.getString("refresh_token","");
        if(refresh.length()<10)return false;
        return refreshToken(c,refresh);
    }

    static void beginAuthorization(Activity a){
        try{
            String verifier=randomUrlSafe(64);
            String state=randomUrlSafe(24);
            String challenge=challenge(verifier);
            a.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit()
                .putString("verifier",verifier)
                .putString("state",state)
                .apply();

            startCallbackServer(a.getApplicationContext());

            Uri u=Uri.parse("https://accounts.spotify.com/authorize").buildUpon()
                .appendQueryParameter("client_id",CLIENT_ID)
                .appendQueryParameter("response_type","code")
                .appendQueryParameter("redirect_uri",REDIRECT_URI)
                .appendQueryParameter("scope",SCOPES)
                .appendQueryParameter("code_challenge_method","S256")
                .appendQueryParameter("code_challenge",challenge)
                .appendQueryParameter("state",state)
                .build();
            a.startActivity(new Intent(Intent.ACTION_VIEW,u));
        }catch(Exception e){
            MediaActions.oauthStatus("Spotify bağlantısı başlatılamadı: "+e.getClass().getSimpleName());
        }
    }

    static synchronized void startCallbackServer(final Context c){
        if(callbackRunning)return;
        callbackRunning=true;
        new Thread(new Runnable(){public void run(){
            ServerSocket server=null;
            try{
                server=new ServerSocket();
                server.setReuseAddress(true);
                server.bind(new InetSocketAddress(InetAddress.getByName("127.0.0.1"),PORT));
                server.setSoTimeout(180000);
                Socket socket=server.accept();
                BufferedReader r=new BufferedReader(new InputStreamReader(socket.getInputStream(),"UTF-8"));
                String request=r.readLine();
                Map<String,String> q=parseRequest(request);
                String expected=c.getSharedPreferences(PREF,Context.MODE_PRIVATE).getString("state","");
                boolean ok=false;
                if(expected.length()>0 && expected.equals(q.get("state")) && q.get("code")!=null){
                    ok=exchangeCode(c,q.get("code"));
                }
                writeBrowserResponse(socket,ok);
                if(ok){
                    MediaActions.oauthStatus("Spotify hesabı bağlandı.");
                    MediaCommandRouter.Command pending=readPending(c);
                    if(pending!=null)SpotifyWebApi.executeFromContext(c,pending);
                }else{
                    MediaActions.oauthStatus("Spotify yetkilendirmesi tamamlanamadı.");
                }
            }catch(Exception e){
                MediaActions.oauthStatus("Spotify OAuth callback başarısız: "+e.getClass().getSimpleName());
            }finally{
                try{if(server!=null)server.close();}catch(Exception ignored){}
                callbackRunning=false;
            }
        }},"jarvis-spotify-callback").start();
    }

    static boolean exchangeCode(Context c,String code)throws Exception{
        SharedPreferences p=c.getSharedPreferences(PREF,Context.MODE_PRIVATE);
        String verifier=p.getString("verifier","");
        String body=form(
            "client_id",CLIENT_ID,
            "grant_type","authorization_code",
            "code",code,
            "redirect_uri",REDIRECT_URI,
            "code_verifier",verifier
        );
        String json=postToken(body);
        return storeToken(c,json,true);
    }

    static boolean refreshToken(Context c,String refresh)throws Exception{
        String body=form(
            "client_id",CLIENT_ID,
            "grant_type","refresh_token",
            "refresh_token",refresh
        );
        String json=postToken(body);
        return storeToken(c,json,false);
    }

    static String postToken(String body)throws Exception{
        URL u=new URL("https://accounts.spotify.com/api/token");
        HttpURLConnection h=(HttpURLConnection)u.openConnection();
        h.setConnectTimeout(7000);h.setReadTimeout(9000);
        h.setRequestMethod("POST");h.setDoOutput(true);
        h.setRequestProperty("Content-Type","application/x-www-form-urlencoded");
        byte[] b=body.getBytes("UTF-8");
        h.getOutputStream().write(b);
        int code=h.getResponseCode();
        InputStream in=code>=200&&code<300?h.getInputStream():h.getErrorStream();
        String out=read(in,300000);
        h.disconnect();
        if(code<200||code>=300)throw new IOException("Spotify token HTTP "+code);
        return out;
    }

    static boolean storeToken(Context c,String json,boolean requireRefresh)throws Exception{
        org.json.JSONObject j=new org.json.JSONObject(json);
        String access=j.optString("access_token","");
        if(access.length()<20)return false;
        int expires=Math.max(60,j.optInt("expires_in",3600));
        SharedPreferences p=c.getSharedPreferences(PREF,Context.MODE_PRIVATE);
        SharedPreferences.Editor e=p.edit()
            .putString("access_token",access)
            .putLong("expires_at",System.currentTimeMillis()+expires*1000L-30000L);
        String refresh=j.optString("refresh_token","");
        if(refresh.length()>10)e.putString("refresh_token",refresh);
        else if(requireRefresh && p.getString("refresh_token","").length()<10){}
        e.apply();
        return true;
    }

    static void rememberPending(Context c,MediaCommandRouter.Command x){
        c.getSharedPreferences(PREF,Context.MODE_PRIVATE).edit()
            .putString("pending_action",x.action)
            .putString("pending_provider",x.provider)
            .putString("pending_query",x.query)
            .putString("pending_artist",x.artist)
            .putString("pending_title",x.title)
            .putString("pending_reply",x.reply)
            .apply();
    }

    static MediaCommandRouter.Command readPending(Context c){
        SharedPreferences p=c.getSharedPreferences(PREF,Context.MODE_PRIVATE);
        String action=p.getString("pending_action","");
        if(action.length()==0)return null;
        MediaCommandRouter.Command x=new MediaCommandRouter.Command(
            action,p.getString("pending_provider","spotify"),
            p.getString("pending_query",""),p.getString("pending_artist",""),
            p.getString("pending_title",""),p.getString("pending_reply",""));
        p.edit().remove("pending_action").apply();
        return x;
    }

    static String challenge(String verifier)throws Exception{
        MessageDigest d=MessageDigest.getInstance("SHA-256");
        return Base64.encodeToString(d.digest(verifier.getBytes("US-ASCII")),Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);
    }

    static String randomUrlSafe(int bytes){
        byte[] b=new byte[bytes];new SecureRandom().nextBytes(b);
        return Base64.encodeToString(b,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);
    }

    static String form(String... kv)throws Exception{
        StringBuilder b=new StringBuilder();
        for(int i=0;i+1<kv.length;i+=2){
            if(b.length()>0)b.append('&');
            b.append(URLEncoder.encode(kv[i],"UTF-8")).append('=').append(URLEncoder.encode(kv[i+1],"UTF-8"));
        }
        return b.toString();
    }

    static Map<String,String> parseRequest(String line)throws Exception{
        HashMap<String,String> m=new HashMap<String,String>();
        if(line==null)return m;
        int a=line.indexOf(' '),b=line.indexOf(' ',a+1);
        if(a<0||b<0)return m;
        String path=line.substring(a+1,b);
        int q=path.indexOf('?');
        if(q<0)return m;
        for(String part:path.substring(q+1).split("&")){
            int e=part.indexOf('=');
            String k=e<0?part:part.substring(0,e);
            String v=e<0?"":part.substring(e+1);
            m.put(URLDecoder.decode(k,"UTF-8"),URLDecoder.decode(v,"UTF-8"));
        }
        return m;
    }

    static void writeBrowserResponse(Socket s,boolean ok)throws Exception{
        String body="<html><body style='font-family:sans-serif;background:#0b0f14;color:white;padding:32px'><h2>"
            +(ok?"Spotify JARVIS'e bağlandı.":"Spotify bağlantısı tamamlanamadı.")
            +"</h2><p>Bu sekmeyi kapatıp JARVIS'e dönebilirsiniz.</p></body></html>";
        byte[] b=body.getBytes("UTF-8");
        OutputStream out=s.getOutputStream();
        String h="HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: "+b.length+"\r\nConnection: close\r\n\r\n";
        out.write(h.getBytes("UTF-8"));out.write(b);out.flush();s.close();
    }

    static String read(InputStream in,int max)throws Exception{
        if(in==null)return "";
        ByteArrayOutputStream o=new ByteArrayOutputStream();byte[] b=new byte[4096];int n,total=0;
        while((n=in.read(b))!=-1){total+=n;if(total>max)throw new IOException("Response too large");o.write(b,0,n);}
        return o.toString("UTF-8");
    }
}
