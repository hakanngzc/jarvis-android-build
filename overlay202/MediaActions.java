package com.hakan.jarvis;

import android.app.Activity;
import android.app.SearchManager;
import android.content.*;
import android.content.pm.PackageManager;
import android.media.AudioManager;
import android.net.Uri;
import android.provider.MediaStore;
import android.view.KeyEvent;

public final class MediaActions {
    public static final String PROFILE="MEDIA_ACTIONS_V1";

    private MediaActions(){}

    public static boolean providerInstalled(Activity a,String provider){
        String pkg=packageFor(provider);
        if(pkg.length()==0)return true;
        try{a.getPackageManager().getPackageInfo(pkg,0);return true;}catch(Exception e){return false;}
    }

    public static void execute(Activity a,MediaCommandRouter.Command c){
        if(c==null)return;
        if("PAUSE".equals(c.action)){mediaKey(a,KeyEvent.KEYCODE_MEDIA_PAUSE);return;}
        if("RESUME".equals(c.action)){mediaKey(a,KeyEvent.KEYCODE_MEDIA_PLAY);return;}
        if("NEXT".equals(c.action)){mediaKey(a,KeyEvent.KEYCODE_MEDIA_NEXT);return;}
        if("PREVIOUS".equals(c.action)){mediaKey(a,KeyEvent.KEYCODE_MEDIA_PREVIOUS);return;}
        if("OPEN".equals(c.action)){openProvider(a,c.provider);return;}
        if("SEARCH".equals(c.action)){search(a,c);return;}
        if("PLAY".equals(c.action)){play(a,c);}
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

    static void play(Activity a,MediaCommandRouter.Command c){
        String pkg=packageFor(c.provider);
        Intent i=new Intent(MediaStore.INTENT_ACTION_MEDIA_PLAY_FROM_SEARCH);
        i.setPackage(pkg);
        i.addCategory(Intent.CATEGORY_DEFAULT);

        String q=c.query==null?"":c.query.trim();
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
