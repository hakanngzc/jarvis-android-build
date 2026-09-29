package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class AppCommandRouter {
    public static final String PROFILE="APP_CONTROL_V1";
    public static final long CONTEXT_WINDOW_MS=120000L;

    public static final class Command {
        public final String action,target,reply;
        public Command(String action,String target,String reply){
            this.action=action;this.target=target;this.reply=reply;
        }
    }

    private AppCommandRouter(){}

    public static Command parse(String raw,String lastTarget,long ageMs){
        String n=normalize(stripWake(raw));
        if(n.length()==0)return null;

        boolean recent=lastTarget!=null&&lastTarget.trim().length()>0&&ageMs>=0&&ageMs<=CONTEXT_WINDOW_MS;

        if(recent&&eqAny(n,"tekrar ac","yeniden ac","geri ac","onu ac","aynisini ac"))
            return open(lastTarget);

        if(recent&&eqAny(n,"onu kapat","uygulamayi kapat","bunu kapat"))
            return close(lastTarget);

        Matcher open=Pattern.compile("^(?:uygulama )?(.+?) (?:uygulamasini )?(?:ac|baslat|calistir|giris yap)$").matcher(n);
        if(open.matches()){
            String target=cleanTarget(open.group(1));
            if(validTarget(target)&&!reserved(target))return open(target);
        }

        Matcher openFirst=Pattern.compile("^(?:ac|baslat|calistir) (.+)$").matcher(n);
        if(openFirst.matches()){
            String target=cleanTarget(openFirst.group(1));
            if(validTarget(target)&&!reserved(target))return open(target);
        }

        Matcher close=Pattern.compile("^(?:uygulama )?(.+?) (?:uygulamasini )?(?:kapat|sonlandir)$").matcher(n);
        if(close.matches()){
            String target=cleanTarget(close.group(1));
            if(validTarget(target)&&!reserved(target))return close(target);
        }

        return null;
    }

    static Command open(String target){
        return new Command("OPEN",target,target+" uygulamasını açıyorum efendim.");
    }

    static Command close(String target){
        return new Command("CLOSE",target,target+" için uygulama yönetimini açıyorum efendim.");
    }

    static String cleanTarget(String target){
        if(target==null)return "";
        String t=target.trim();
        t=t.replaceFirst("^(?:uygulama )","");
        t=t.replaceAll("(?: yi| i| yu| u| yi| i)$","");
        t=t.replaceAll("(?iu)(?:yi|yı|yu|yü)$","");
        if(t.equals("ayarlari"))t="ayarlar";
        else if(t.equals("kamerayi"))t="kamera";
        else if(t.equals("galeriyi"))t="galeri";
        else if(t.equals("rehberi"))t="rehber";
        t=t.replaceAll("\\s+"," ").trim();
        if("kamerayi".equals(t))t="kamera";
        else if("ayarlari".equals(t))t="ayarlar";
        else if("galeriyi".equals(t))t="galeri";
        else if("rehberi".equals(t))t="rehber";
        return t;
    }

    static boolean validTarget(String t){
        return t!=null&&t.length()>=2&&t.length()<=60;
    }

    static boolean reserved(String t){
        String n=normalize(t);
        return n.matches(".*\\b(?:alarm|fener|feneri|flash|flas|flasi|wifi|wi fi|bluetooth|blutut|sarki|muzik|ses|arama|ara)\\b.*");
    }

    static boolean eqAny(String s,String... values){
        for(String v:values)if(s.equals(v))return true;
        return false;
    }

    static String stripWake(String raw){
        if(raw==null)return "";
        return raw.trim().replaceFirst("(?iu)^(hey )?([jc]arvi[sz]|[cj]ervis)[,:]?\\s+","");
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
