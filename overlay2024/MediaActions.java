package com.hakan.jarvis;

import android.app.Activity;
import android.app.SearchManager;
import android.content.*;
import android.content.pm.PackageManager;
import android.media.AudioManager;
import android.media.session.MediaController;
import android.media.session.MediaSessionManager;
import android.media.session.PlaybackState;
import android.net.Uri;
import android.provider.Settings;
import android.provider.MediaStore;
import android.view.KeyEvent;

public final class MediaActions {
    public static final String PROFILE="MEDIA_ACTIONS_V4_SPOTIFY_WEB_API";

    private MediaActions(){}

    public static boolean providerInstalled(Activity a,String provider){
        String pkg=packageFor(provider);
        if(pkg.length()==0)return true;
        try{a.getPackageManager().getPackageInfo(pkg,0);return true;}catch(Exception e){return false;}
    }

    public static void execute(Activity a,MediaCommandRouter.Command c){
        if(c==null)return;
        if("AUTH".equals(c.action)&&"spotify".equals(c.provider)){spotifyAuthorize(a,null);return;}

        if(isTransportAction(c)&&"spotify".equals(c.provider)&&SpotifyOAuthManager.isLinked(a)){
            spotifyControl(a,c);return;
        }

        if("PAUSE".equals(c.action)){if(!sessionControl(a,c.provider,"PAUSE"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PAUSE);return;}
        if("RESUME".equals(c.action)){if(!sessionControl(a,c.provider,"RESUME"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PLAY);return;}
        if("NEXT".equals(c.action)){if(!sessionControl(a,c.provider,"NEXT"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_NEXT);return;}
        if("PREVIOUS".equals(c.action)){if(!sessionControl(a,c.provider,"PREVIOUS"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PREVIOUS);return;}
        if("OPEN".equals(c.action)){openProvider(a,c.provider);return;}
        if("SEARCH".equals(c.action)){search(a,c);return;}
        if("PLAY".equals(c.action)){
            if("spotify".equals(c.provider))spotifyPlay(a,c);
            else play(a,c);
        }
    }


    static void spotifyAuthorize(final Activity a,final MediaCommandRouter.Command pending){
        SpotifyOAuthManager.authorize(a,new SpotifyOAuthManager.Callback(){
            public void onAuthorized(){
                android.widget.Toast.makeText(a,"Spotify JARVIS'e bağlandı.",android.widget.Toast.LENGTH_SHORT).show();
                if(pending!=null)spotifyPlay(a,pending);
            }
            public void onError(String message){
                android.widget.Toast.makeText(a,message,android.widget.Toast.LENGTH_LONG).show();
            }
        });
    }

    static void spotifyControl(final Activity a,final MediaCommandRouter.Command c){
        java.util.concurrent.Executors.newSingleThreadExecutor().execute(new Runnable(){public void run(){
            boolean ok=false;
            try{ok=SpotifyWebApi.control(a,c.action);}catch(Exception ignored){}
            final boolean success=ok;
            a.runOnUiThread(new Runnable(){public void run(){
                if(success)return;
                try{
                    if(!sessionControl(a,c.provider,c.action)){
                        if("PAUSE".equals(c.action))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PAUSE);
                        else if("RESUME".equals(c.action))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PLAY);
                        else if("NEXT".equals(c.action))mediaKey(a,KeyEvent.KEYCODE_MEDIA_NEXT);
                        else if("PREVIOUS".equals(c.action))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PREVIOUS);
                    }
                }catch(Exception ignored){}
            }});
        }});
    }

    static void spotifyPlay(final Activity a,final MediaCommandRouter.Command c){
        if(!SpotifyOAuthManager.isLinked(a)){
            spotifyAuthorize(a,c);
            return;
        }

        java.util.concurrent.Executors.newSingleThreadExecutor().execute(new Runnable(){public void run(){
            MediaCommandRouter.Command chosen=c;
            try{
                ExactSongResolver.Result r=ExactSongResolver.resolve(c,new ExactSongResolver.HttpsTransport());
                if(r!=null&&r.resolved&&r.query.length()>0)
                    chosen=new MediaCommandRouter.Command(c.action,c.provider,r.query,r.artist,r.title,c.reply);
            }catch(Exception ignored){}

            SpotifyWebApi.PlayResult result=null;
            try{
                result=SpotifyWebApi.playExact(a,chosen.artist,chosen.title,chosen.query);
                if(result!=null&&result.success)return;
            }catch(SpotifyWebApi.AuthRequiredException auth){
                final MediaCommandRouter.Command again=chosen;
                a.runOnUiThread(new Runnable(){public void run(){spotifyAuthorize(a,again);}});
                return;
            }catch(Exception ignored){}

            if(result!=null&&result.track!=null){
                final SpotifyWebApi.Track track=result.track;
                try{
                    a.runOnUiThread(new Runnable(){public void run(){
                        try{
                            Intent i=new Intent(Intent.ACTION_VIEW,Uri.parse(track.uri)).setPackage("com.spotify.music");
                            a.startActivity(i);
                        }catch(Exception ignored){}
                    }});
                    Thread.sleep(1600L);
                    try{
                        SpotifyWebApi.PlayResult retry=SpotifyWebApi.playExact(a,chosen.artist,chosen.title,chosen.query);
                        if(retry!=null&&retry.success)return;
                    }catch(Exception ignored){}
                    final String uri=track.uri;
                    a.runOnUiThread(new Runnable(){public void run(){
                        if(sessionPlayFromUri(a,"spotify",uri))return;
                        playResolved(a,new MediaCommandRouter.Command("PLAY","spotify",track.artist+" "+track.name,track.artist,track.name,c.reply));
                    }});
                    return;
                }catch(Exception ignored){}
            }

            final MediaCommandRouter.Command fallback=chosen;
            a.runOnUiThread(new Runnable(){public void run(){playResolved(a,fallback);}});
        }});
    }

    static boolean sessionPlayFromUri(Activity a,String provider,String uri){
        if(!hasSessionAccess(a))return false;
        try{
            MediaSessionManager msm=(MediaSessionManager)a.getSystemService(Context.MEDIA_SESSION_SERVICE);
            if(msm==null)return false;
            java.util.List<MediaController> sessions=msm.getActiveSessions(new ComponentName(a,JarvisMediaListener.class));
            if(sessions==null||sessions.isEmpty())return false;
            MediaController target=chooseSession(sessions,provider);
            if(target==null)return false;
            target.getTransportControls().playFromUri(Uri.parse(uri),new android.os.Bundle());
            return true;
        }catch(Exception e){return false;}
    }

    public static boolean isTransportAction(MediaCommandRouter.Command c){
        if(c==null)return false;
        return "PAUSE".equals(c.action)||"RESUME".equals(c.action)||"NEXT".equals(c.action)||"PREVIOUS".equals(c.action);
    }

    public static boolean hasSessionAccess(Activity a){
        try{
            String enabled=Settings.Secure.getString(a.getContentResolver(),"enabled_notification_listeners");
            if(enabled==null)return false;
            String me=new ComponentName(a,JarvisMediaListener.class).flattenToString();
            String pkg=a.getPackageName();
            return enabled.contains(me)||enabled.contains(pkg);
        }catch(Exception e){return false;}
    }

    public static void requestSessionAccess(Activity a){
        try{
            Intent i=new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
            a.startActivity(i);
        }catch(Exception e){
            Intent i=new Intent("android.settings.NOTIFICATION_LISTENER_SETTINGS");
            a.startActivity(i);
        }
    }

    static boolean sessionControl(Activity a,String provider,String action){
        if(!hasSessionAccess(a))return false;
        try{
            MediaSessionManager msm=(MediaSessionManager)a.getSystemService(Context.MEDIA_SESSION_SERVICE);
            if(msm==null)return false;
            ComponentName listener=new ComponentName(a,JarvisMediaListener.class);
            java.util.List<MediaController> sessions=msm.getActiveSessions(listener);
            if(sessions==null||sessions.isEmpty())return false;

            MediaController target=chooseSession(sessions,provider);
            if(target==null)return false;

            MediaController.TransportControls t=target.getTransportControls();
            if("PAUSE".equals(action)){t.pause();return true;}
            if("RESUME".equals(action)){t.play();return true;}
            if("NEXT".equals(action)){t.skipToNext();return true;}
            if("PREVIOUS".equals(action)){t.skipToPrevious();return true;}
        }catch(SecurityException e){return false;}
        catch(Exception e){return false;}
        return false;
    }

    static MediaController chooseSession(java.util.List<MediaController> sessions,String provider){
        String wanted=packageFor(provider);
        if(wanted.length()>0){
            for(MediaController c:sessions)if(wanted.equals(c.getPackageName()))return c;
        }

        MediaController recognizedPlaying=null;
        MediaController anyPlaying=null;
        MediaController recognizedAny=null;

        for(MediaController c:sessions){
            String pkg=c.getPackageName();
            boolean recognized="com.spotify.music".equals(pkg)
                ||"com.google.android.apps.youtube.music".equals(pkg)
                ||"com.google.android.youtube".equals(pkg);
            PlaybackState st=c.getPlaybackState();
            boolean playing=st!=null&&(st.getState()==PlaybackState.STATE_PLAYING
                ||st.getState()==PlaybackState.STATE_BUFFERING
                ||st.getState()==PlaybackState.STATE_CONNECTING);

            if(recognized&&playing&&recognizedPlaying==null)recognizedPlaying=c;
            if(playing&&anyPlaying==null)anyPlaying=c;
            if(recognized&&recognizedAny==null)recognizedAny=c;
        }

        if(recognizedPlaying!=null)return recognizedPlaying;
        if(anyPlaying!=null)return anyPlaying;
        if(recognizedAny!=null)return recognizedAny;
        return sessions.get(0);
    }

    static void mediaKey(Activity a,int code){
        AudioManager am=(AudioManager)a.getSystemService(Context.AUDIO_SERVICE);
        if(am==null)throw new IllegalStateException("Medya servisi kullanılamıyor");
        long t=android.os.SystemClock.uptimeMillis();
        am.dispatchMediaKeyEvent(new KeyEvent(t,t,KeyEvent.ACTION_DOWN,code,0));
        am.dispatchMediaKeyEvent(new KeyEvent(t,t,KeyEvent.ACTION_UP,code,0));
    }

    static void openProvider(Activity a,String provider){
        String pkg=packageFor(provider);
        Intent i=a.getPackageManager().getLaunchIntentForPackage(pkg);
        if(i==null)throw new IllegalStateException(MediaCommandRouter.providerName(provider)+" yüklü değil");
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
        a.startActivity(i);
    }

    static void play(final Activity a,final MediaCommandRouter.Command c){
        java.util.concurrent.Executors.newSingleThreadExecutor().execute(new Runnable(){public void run(){
            MediaCommandRouter.Command chosen=c;
            try{
                ExactSongResolver.Result r=ExactSongResolver.resolve(c,new ExactSongResolver.HttpsTransport());
                if(r!=null&&r.resolved&&r.query.length()>0)
                    chosen=new MediaCommandRouter.Command(c.action,c.provider,r.query,r.artist,r.title,c.reply);
            }catch(Exception ignored){}
            final MediaCommandRouter.Command finalCommand=chosen;
            a.runOnUiThread(new Runnable(){public void run(){playResolved(a,finalCommand);}});
        }});
    }

    static void playResolved(Activity a,MediaCommandRouter.Command c){
        String q=c.query==null?"":c.query.trim();

        if(hasSessionAccess(a)&&sessionPlayFromSearch(a,c.provider,q,c.artist,c.title))return;

        String pkg=packageFor(c.provider);
        Intent i=new Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH);
        i.setPackage(pkg);
        i.addCategory(Intent.CATEGORY_DEFAULT);

        if("youtube".equals(c.provider)&&c.artist!=null&&c.artist.length()>0&&c.title!=null&&c.title.length()>0)
            q=(c.artist+" "+c.title+" official audio").trim();

        i.putExtra(SearchManager.QUERY,q);

        if(c.title!=null&&c.title.length()>0){
            i.putExtra(MediaStore.EXTRA_MEDIA_FOCUS,MediaStore.Audio.Media.ENTRY_CONTENT_TYPE);
            i.putExtra(MediaStore.EXTRA_MEDIA_TITLE,c.title);
            if(c.artist!=null&&c.artist.length()>0)i.putExtra(MediaStore.EXTRA_MEDIA_ARTIST,c.artist);
        }else if(c.artist!=null&&c.artist.length()>0){
            i.putExtra(MediaStore.EXTRA_MEDIA_FOCUS,MediaStore.Audio.Artists.ENTRY_CONTENT_TYPE);
            i.putExtra(MediaStore.EXTRA_MEDIA_ARTIST,c.artist);
        }else{
            i.putExtra(MediaStore.EXTRA_MEDIA_FOCUS,"vnd.android.cursor.item/*");
        }

        PackageManager pm=a.getPackageManager();
        if(i.resolveActivity(pm)!=null){a.startActivity(i);return;}

        search(a,c);
    }

    static boolean sessionPlayFromSearch(Activity a,String provider,String query,String artist,String title){
        try{
            MediaSessionManager msm=(MediaSessionManager)a.getSystemService(Context.MEDIA_SESSION_SERVICE);
            if(msm==null)return false;
            ComponentName listener=new ComponentName(a,JarvisMediaListener.class);
            java.util.List<MediaController> sessions=msm.getActiveSessions(listener);
            if(sessions==null||sessions.isEmpty())return false;
            MediaController target=chooseSession(sessions,provider);
            if(target==null)return false;

            android.os.Bundle extras=new android.os.Bundle();
            if(title!=null&&title.length()>0){
                extras.putString(MediaStore.EXTRA_MEDIA_TITLE,title);
                extras.putString(MediaStore.EXTRA_MEDIA_FOCUS,MediaStore.Audio.Media.ENTRY_CONTENT_TYPE);
            }
            if(artist!=null&&artist.length()>0)extras.putString(MediaStore.EXTRA_MEDIA_ARTIST,artist);

            target.getTransportControls().playFromSearch(query,extras);
            return true;
        }catch(SecurityException e){return false;}
        catch(Exception e){return false;}
    }

    static void search(Activity a,MediaCommandRouter.Command c){
        String pkg=packageFor(c.provider);
        String q=c.query==null?"":c.query.trim();

        if("spotify".equals(c.provider)){
            try{
                Intent i=new Intent(Intent.ACTION_VIEW,Uri.parse("spotify:search:"+Uri.encode(q))).setPackage(pkg);
                if(i.resolveActivity(a.getPackageManager())!=null){a.startActivity(i);return;}
            }catch(Exception ignored){}
        }

        if("youtube".equals(c.provider)){
            try{
                Intent i=new Intent(Intent.ACTION_SEARCH).setPackage(pkg).putExtra(SearchManager.QUERY,q);
                if(i.resolveActivity(a.getPackageManager())!=null){a.startActivity(i);return;}
            }catch(Exception ignored){}
            Intent w=new Intent(Intent.ACTION_VIEW,Uri.parse("https://www.youtube.com/results?search_query="+Uri.encode(q))).setPackage(pkg);
            a.startActivity(w);return;
        }

        if("youtube_music".equals(c.provider)){
            try{
                Intent i=new Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH).setPackage(pkg)
                    .putExtra(MediaStore.EXTRA_MEDIA_FOCUS,"vnd.android.cursor.item/*")
                    .putExtra(SearchManager.QUERY,q);
                if(i.resolveActivity(a.getPackageManager())!=null){a.startActivity(i);return;}
            }catch(Exception ignored){}
            Intent w=new Intent(Intent.ACTION_VIEW,Uri.parse("https://music.youtube.com/search?q="+Uri.encode(q))).setPackage(pkg);
            a.startActivity(w);return;
        }

        throw new IllegalStateException(MediaCommandRouter.providerName(c.provider)+" araması açılamadı");
    }

    static String packageFor(String provider){
        if("youtube".equals(provider))return "com.google.android.youtube";
        if("youtube_music".equals(provider))return "com.google.android.apps.youtube.music";
        if("spotify".equals(provider))return "com.spotify.music";
        return "";
    }
}
