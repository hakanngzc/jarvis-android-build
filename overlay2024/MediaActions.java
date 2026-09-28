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
    public static final String PROFILE="MEDIA_ACTIONS_V4_SPOTIFY_OAUTH";

    private MediaActions(){}

    public static boolean providerInstalled(Activity a,String provider){
        String pkg=packageFor(provider);
        if(pkg.length()==0)return true;
        try{a.getPackageManager().getPackageInfo(pkg,0);return true;}catch(Exception e){return false;}
    }

    public static void execute(Activity a,MediaCommandRouter.Command c){
        if(c==null)return;
        if("spotify".equals(c.provider)&&SpotifyOAuthManager.handle(a,c))return;
        executeLegacy(a,c);
    }

    public static void executeLegacy(Activity a,MediaCommandRouter.Command c){
        if(c==null)return;
        if("PAUSE".equals(c.action)){if(!sessionControl(a,c.provider,"PAUSE"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PAUSE);return;}
        if("RESUME".equals(c.action)){if(!sessionControl(a,c.provider,"RESUME"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PLAY);return;}
        if("NEXT".equals(c.action)){if(!sessionControl(a,c.provider,"NEXT"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_NEXT);return;}
        if("PREVIOUS".equals(c.action)){if(!sessionControl(a,c.provider,"PREVIOUS"))mediaKey(a,KeyEvent.KEYCODE_MEDIA_PREVIOUS);return;}
        if("OPEN".equals(c.action)){openProvider(a,c.provider);return;}
        if("SEARCH".equals(c.action)){search(a,c);return;}
        if("PLAY".equals(c.action)){play(a,c);}
    }

    public static void oauthStatus(String message){
        android.util.Log.i("JARVIS_SPOTIFY",message==null?"":message);
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
