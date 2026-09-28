package com.hakan.jarvis;

import android.app.Activity;
import android.content.*;
import android.content.pm.*;
import android.net.Uri;
import android.provider.MediaStore;
import android.provider.Settings;
import android.provider.ContactsContract;

import java.text.Normalizer;
import java.util.*;

public final class AppActions {
    public static final String PROFILE="APP_ACTIONS_V1";

    public static final class Result {
        public final boolean success;
        public final boolean managementFallback;
        public final String resolvedLabel,packageName,note;

        Result(boolean success,boolean managementFallback,String label,String pkg,String note){
            this.success=success;this.managementFallback=managementFallback;
            this.resolvedLabel=label==null?"":label;
            this.packageName=pkg==null?"":pkg;
            this.note=note==null?"":note;
        }
    }

    static final class Candidate{
        final String label,pkg;final int score;
        Candidate(String label,String pkg,int score){this.label=label;this.pkg=pkg;this.score=score;}
    }

    private AppActions(){}

    public static Result execute(Activity a,AppCommandRouter.Command c){
        if(c==null)throw new IllegalArgumentException("command");
        if("OPEN".equals(c.action))return open(a,c.target);
        if("CLOSE".equals(c.action))return closeUnsupported(a,c.target);
        throw new IllegalArgumentException("Unsupported app action");
    }

    public static Result open(Activity a,String target){
        String n=normalize(target);

        Result special=openSpecial(a,n);
        if(special!=null)return special;

        Candidate c=resolveLaunchable(a,target);
        if(c==null)return new Result(false,false,"","","Uygulama bulunamadı.");

        try{
            Intent i=a.getPackageManager().getLaunchIntentForPackage(c.pkg);
            if(i==null)return new Result(false,false,c.label,c.pkg,"Başlatma intent'i bulunamadı.");
            i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED);
            a.startActivity(i);
            return new Result(true,false,c.label,c.pkg,"Uygulama açıldı.");
        }catch(Exception e){
            return new Result(false,false,c.label,c.pkg,e.getClass().getSimpleName());
        }
    }

    public static Result closeUnsupported(Activity a,String target){
        Candidate c=resolveLaunchable(a,target);
        if(c==null)return new Result(false,false,"","","Uygulama bulunamadı.");

        try{
            Intent details=new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+c.pkg));
            a.startActivity(details);
            return new Result(false,true,c.label,c.pkg,"Android üçüncü taraf uygulamayı doğrudan force-stop etmeye izin vermiyor.");
        }catch(Exception e){
            return new Result(false,false,c.label,c.pkg,e.getClass().getSimpleName());
        }
    }

    static Result openSpecial(Activity a,String n){
        try{
            if(eqAny(n,"ayarlar","ayarlari","ayar","telefon ayarlari","telefon ayarlari uygulamasi")){
                a.startActivity(new Intent(Settings.ACTION_SETTINGS));
                return new Result(true,false,"Ayarlar","android.settings","Sistem ayarları açıldı.");
            }
            if(eqAny(n,"kamera","kamerayi","fotograf makinesi")){
                Intent i=new Intent(MediaStore.INTENT_ACTION_STILL_IMAGE_CAMERA);
                a.startActivity(i);
                return new Result(true,false,"Kamera","","Kamera açıldı.");
            }
            if(eqAny(n,"galeri","galeriyi","fotograflar","fotograflarim")){
                Intent i=new Intent(Intent.ACTION_VIEW,MediaStore.Images.Media.EXTERNAL_CONTENT_URI);
                i.setType("image/*");
                a.startActivity(i);
                return new Result(true,false,"Galeri","","Galeri açıldı.");
            }
            if(eqAny(n,"rehber","rehberi","kisiler","kontaktlar")){
                Intent i=new Intent(Intent.ACTION_VIEW,ContactsContract.Contacts.CONTENT_URI);
                a.startActivity(i);
                return new Result(true,false,"Kişiler","","Kişiler açıldı.");
            }
        }catch(Exception ignored){}
        return null;
    }

    static Candidate resolveLaunchable(Activity a,String target){
        PackageManager pm=a.getPackageManager();
        String q=normalize(alias(target));

        Intent launcher=new Intent(Intent.ACTION_MAIN,null);
        launcher.addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> infos;
        try{infos=pm.queryIntentActivities(launcher,0);}catch(Exception e){return null;}
        if(infos==null)return null;

        Candidate best=null;
        for(ResolveInfo ri:infos){
            if(ri==null||ri.activityInfo==null)continue;
            String pkg=ri.activityInfo.packageName;
            if(pkg==null||pkg.equals(a.getPackageName()))continue;

            CharSequence cs=ri.loadLabel(pm);
            String label=cs==null?"":cs.toString().trim();
            if(label.length()==0)continue;

            int score=matchScore(q,normalize(label),normalize(pkg));
            if(score<=0)continue;
            Candidate c=new Candidate(label,pkg,score);
            if(best==null||c.score>best.score)best=c;
        }
        return best!=null&&best.score>=55?best:null;
    }

    static String alias(String target){
        String n=normalize(target);
        if(eqAny(n,"x","twitter"))return "twitter";
        if(eqAny(n,"insta"))return "instagram";
        if(eqAny(n,"wp","watsap","whatsap"))return "whatsapp";
        if(eqAny(n,"google haritalar","haritalar"))return "maps";
        if(eqAny(n,"google fotograflar"))return "photos";
        return target==null?"":target;
    }

    static int matchScore(String q,String label,String pkg){
        if(q.length()==0)return 0;
        if(label.equals(q))return 120;
        if(pkg.equals(q))return 115;
        if(label.startsWith(q)||q.startsWith(label))return 95;
        if(label.contains(q)||q.contains(label))return 85;

        Set<String> qt=tokens(q),lt=tokens(label+" "+pkg.replace('.',' '));
        if(qt.isEmpty())return 0;
        int hit=0;for(String x:qt)if(lt.contains(x))hit++;
        return (int)Math.round(70.0*hit/qt.size());
    }

    static Set<String> tokens(String s){
        LinkedHashSet<String> out=new LinkedHashSet<String>();
        for(String x:normalize(s).split(" "))if(x.length()>1)out.add(x);
        return out;
    }

    static boolean eqAny(String s,String... values){
        for(String v:values)if(s.equals(v))return true;
        return false;
    }

    static String normalize(String raw){
        if(raw==null)return "";
        String s=raw.trim().toLowerCase(new Locale("tr","TR"));
        s=s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s=Normalizer.normalize(s,Normalizer.Form.NFD).replaceAll("\\p{M}+","");
        s=s.replace('’',' ').replace('\'',' ');
        s=s.replaceAll("[^a-z0-9 ]+"," ");
        return s.replaceAll("\\s+"," ").trim();
    }
}
