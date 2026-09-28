package com.hakan.jarvis;

import android.app.Activity;
import android.content.*;
import android.net.Uri;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONObject;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.io.*;
import java.net.*;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.KeyStore;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class SpotifyOAuthManager {
    public static final String PROFILE="SPOTIFY_OAUTH_PKCE_V1";
    public static final String CLIENT_ID="e6a9bcc48fc34959aa5914e46efb1a44";
    public static final String REDIRECT_URI="http://127.0.0.1:43821/callback";
    public static final String SCOPES="user-read-playback-state user-modify-playback-state user-read-currently-playing";

    private static final String PREFS="jarvis_spotify_oauth";
    private static final String KEY_ALIAS="jarvis_spotify_token_key_v1";
    private static final ExecutorService EXEC=Executors.newSingleThreadExecutor();

    public interface Callback{
        void onAuthorized();
        void onError(String message);
    }

    private SpotifyOAuthManager(){}

    public static boolean isLinked(Context c){
        SharedPreferences p=c.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
        return p.contains("access")||p.contains("refresh");
    }

    public static void disconnect(Context c){
        c.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().clear().apply();
    }

    public static void authorize(final Activity a,final Callback cb){
        EXEC.execute(new Runnable(){public void run(){
            ServerSocket server=null;
            try{
                final String verifier=randomUrlSafe(64);
                final String state=randomUrlSafe(24);
                final String challenge=codeChallenge(verifier);

                server=new ServerSocket();
                server.setReuseAddress(true);
                server.bind(new InetSocketAddress(InetAddress.getByName("127.0.0.1"),43821));
                server.setSoTimeout(180000);

                final String auth="https://accounts.spotify.com/authorize"
                    +"?response_type=code"
                    +"&client_id="+enc(CLIENT_ID)
                    +"&scope="+enc(SCOPES)
                    +"&redirect_uri="+enc(REDIRECT_URI)
                    +"&state="+enc(state)
                    +"&code_challenge_method=S256"
                    +"&code_challenge="+enc(challenge)
                    +"&show_dialog=false";

                a.runOnUiThread(new Runnable(){public void run(){
                    try{a.startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(auth)));}
                    catch(Exception e){finishError(a,cb,"Spotify giriş ekranı açılamadı.");}
                }});

                Socket socket=server.accept();
                socket.setSoTimeout(10000);
                BufferedReader br=new BufferedReader(new InputStreamReader(socket.getInputStream(),StandardCharsets.UTF_8));
                String first=br.readLine();
                if(first==null||!first.startsWith("GET "))throw new IOException("Invalid callback");
                String target=first.substring(4,first.indexOf(' ',4));
                Uri u=Uri.parse("http://127.0.0.1"+target);
                String gotState=u.getQueryParameter("state");
                String code=u.getQueryParameter("code");
                String error=u.getQueryParameter("error");

                OutputStream out=socket.getOutputStream();
                String body="<html><body style='font-family:sans-serif;background:#101214;color:#fff;padding:32px'>"
                    +"<h2>JARVIS Spotify</h2><p>"+(error==null?"Bağlantı tamamlandı. JARVIS'e dönebilirsiniz.":"Bağlantı reddedildi.")+"</p></body></html>";
                byte[] bytes=body.getBytes(StandardCharsets.UTF_8);
                String headers="HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: "+bytes.length+"\r\nConnection: close\r\n\r\n";
                out.write(headers.getBytes(StandardCharsets.UTF_8));
                out.write(bytes);out.flush();
                socket.close();

                if(error!=null)throw new IOException("Spotify authorization denied: "+error);
                if(code==null||!state.equals(gotState))throw new SecurityException("OAuth state mismatch");

                Token t=exchangeCode(code,verifier);
                saveToken(a,t);
                finishOk(a,cb);
            }catch(SocketTimeoutException e){
                finishError(a,cb,"Spotify bağlantısı zaman aşımına uğradı.");
            }catch(Exception e){
                finishError(a,cb,"Spotify hesabı bağlanamadı: "+e.getClass().getSimpleName());
            }finally{
                try{if(server!=null)server.close();}catch(Exception ignored){}
            }
        }});
    }

    public static String getValidAccessToken(Context c)throws Exception{
        SharedPreferences p=c.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
        String access=decryptStored(p.getString("access",null));
        long expiry=p.getLong("expiry",0L);
        if(access!=null&&access.length()>0&&System.currentTimeMillis()<expiry-60000L)return access;

        String refresh=decryptStored(p.getString("refresh",null));
        if(refresh==null||refresh.length()==0)return null;

        Token t=refreshToken(refresh);
        if(t.refresh==null||t.refresh.length()==0)t.refresh=refresh;
        saveToken(c,t);
        return t.access;
    }

    public static void invalidateAccess(Context c){
        c.getSharedPreferences(PREFS,Context.MODE_PRIVATE).edit().putLong("expiry",0L).apply();
    }

    static final class Token{
        String access,refresh;
        long expiresIn;
    }

    static Token exchangeCode(String code,String verifier)throws Exception{
        String form="client_id="+enc(CLIENT_ID)
            +"&grant_type=authorization_code"
            +"&code="+enc(code)
            +"&redirect_uri="+enc(REDIRECT_URI)
            +"&code_verifier="+enc(verifier);
        return tokenRequest(form);
    }

    static Token refreshToken(String refresh)throws Exception{
        String form="client_id="+enc(CLIENT_ID)
            +"&grant_type=refresh_token"
            +"&refresh_token="+enc(refresh);
        return tokenRequest(form);
    }

    static Token tokenRequest(String form)throws Exception{
        HttpURLConnection c=(HttpURLConnection)new URL("https://accounts.spotify.com/api/token").openConnection();
        c.setConnectTimeout(7000);c.setReadTimeout(9000);
        c.setRequestMethod("POST");c.setDoOutput(true);
        c.setRequestProperty("Content-Type","application/x-www-form-urlencoded");
        byte[] data=form.getBytes(StandardCharsets.UTF_8);
        OutputStream out=c.getOutputStream();out.write(data);out.close();
        int code=c.getResponseCode();
        String raw=read(code>=200&&code<300?c.getInputStream():c.getErrorStream(),300000);
        c.disconnect();
        if(code<200||code>=300)throw new IOException("Spotify token HTTP "+code);
        JSONObject j=new JSONObject(raw);
        Token t=new Token();
        t.access=j.optString("access_token","");
        t.refresh=j.optString("refresh_token","");
        t.expiresIn=j.optLong("expires_in",3600L);
        if(t.access.length()==0)throw new IOException("Spotify access token missing");
        return t;
    }

    static void saveToken(Context c,Token t)throws Exception{
        SharedPreferences p=c.getSharedPreferences(PREFS,Context.MODE_PRIVATE);
        SharedPreferences.Editor e=p.edit();
        e.putString("access",encryptStored(t.access));
        if(t.refresh!=null&&t.refresh.length()>0)e.putString("refresh",encryptStored(t.refresh));
        e.putLong("expiry",System.currentTimeMillis()+Math.max(60L,t.expiresIn)*1000L);
        e.apply();
    }

    static String encryptStored(String plain)throws Exception{
        if(plain==null)return null;
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.ENCRYPT_MODE,key());
        byte[] iv=cipher.getIV();
        byte[] enc=cipher.doFinal(plain.getBytes(StandardCharsets.UTF_8));
        return Base64.encodeToString(iv,Base64.NO_WRAP)+":"+Base64.encodeToString(enc,Base64.NO_WRAP);
    }

    static String decryptStored(String stored)throws Exception{
        if(stored==null||stored.length()==0)return null;
        String[] p=stored.split(":",2);
        if(p.length!=2)return null;
        byte[] iv=Base64.decode(p[0],Base64.NO_WRAP);
        byte[] enc=Base64.decode(p[1],Base64.NO_WRAP);
        Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,iv));
        return new String(cipher.doFinal(enc),StandardCharsets.UTF_8);
    }

    static SecretKey key()throws Exception{
        KeyStore ks=KeyStore.getInstance("AndroidKeyStore");ks.load(null);
        java.security.Key k=ks.getKey(KEY_ALIAS,null);
        if(k instanceof SecretKey)return (SecretKey)k;
        KeyGenerator kg=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");
        kg.init(new KeyGenParameterSpec.Builder(KEY_ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .build());
        return kg.generateKey();
    }

    static String codeChallenge(String verifier)throws Exception{
        MessageDigest md=MessageDigest.getInstance("SHA-256");
        byte[] digest=md.digest(verifier.getBytes(StandardCharsets.US_ASCII));
        return Base64.encodeToString(digest,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);
    }

    static String randomUrlSafe(int bytes){
        byte[] b=new byte[bytes];new SecureRandom().nextBytes(b);
        return Base64.encodeToString(b,Base64.URL_SAFE|Base64.NO_WRAP|Base64.NO_PADDING);
    }

    static String enc(String s)throws Exception{return URLEncoder.encode(s,"UTF-8");}

    static String read(InputStream in,int max)throws Exception{
        if(in==null)return "";
        ByteArrayOutputStream out=new ByteArrayOutputStream();
        byte[] buf=new byte[4096];int n,total=0;
        while((n=in.read(buf))!=-1){total+=n;if(total>max)throw new IOException("Response too large");out.write(buf,0,n);}
        in.close();return out.toString("UTF-8");
    }

    static void finishOk(final Activity a,final Callback cb){
        a.runOnUiThread(new Runnable(){public void run(){if(cb!=null)cb.onAuthorized();}});
    }

    static void finishError(final Activity a,final Callback cb,final String m){
        a.runOnUiThread(new Runnable(){public void run(){if(cb!=null)cb.onError(m);}});
    }
}
