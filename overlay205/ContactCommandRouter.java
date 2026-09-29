package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class ContactCommandRouter {
    public static final String PROFILE="CONTACT_INTELLIGENCE_V1";
    public static final long CONTEXT_WINDOW_MS=5L*60L*1000L;

    public static final class Command {
        public final String action;
        public final String target;
        public final String message;
        public final String channel;

        public Command(String action,String target,String message,String channel){
            this.action=action==null?"":action;
            this.target=target==null?"":target.trim();
            this.message=message==null?"":message.trim();
            this.channel=channel==null?"":channel;
        }

        public Command withMessage(String text){
            return new Command(action,target,text,channel);
        }
    }

    private ContactCommandRouter(){}

    public static Command parse(String raw,String lastContact,long ageMs){
        String original=stripWake(raw).trim();
        String n=normalize(original);
        if(n.length()==0)return null;
        boolean recent=lastContact!=null&&lastContact.trim().length()>0&&ageMs>=0&&ageMs<=CONTEXT_WINDOW_MS;

        if(recent){
            if(eqAny(n,"onu ara","tekrar ara","onu tekrar ara","bir daha ara"))
                return new Command("CALL",lastContact,"","call");

            Matcher ctxWaMsg=Pattern.compile("^(?:olmadi )?(?:ona )?whatsapp (?:tan|dan) (.+?) (?:yaz|gonder)$").matcher(n);
            if(ctxWaMsg.matches())
                return new Command("MESSAGE",lastContact,recoverContextWhatsAppMessage(original,cleanMessage(ctxWaMsg.group(1))),"whatsapp");

            if(n.matches("^(?:olmadi )?(?:ona )?whatsapp (?:tan|dan) (?:yaz|mesaj at|mesaj gonder)$")
                    || eqAny(n,"whatsapptan yaz","ona whatsapptan yaz","olmadı whatsapptan yaz"))
                return new Command("MESSAGE",lastContact,"","whatsapp");

            Matcher ctxSmsMsg=Pattern.compile("^(?:ona )?(?:mesaj|sms) (?:at|gonder) (.+)$").matcher(n);
            if(ctxSmsMsg.matches())
                return new Command("MESSAGE",lastContact,recoverContextSmsMessage(original,cleanMessage(ctxSmsMsg.group(1))),"sms");

            if(n.matches("^(?:ona )?(?:mesaj|sms) (?:at|gonder)$"))
                return new Command("MESSAGE",lastContact,"","sms");
        }

        Matcher waWithText=Pattern.compile("^(.+?) (?:e|a) whatsapp (?:tan|dan) (.+?) (?:yaz|gonder)$").matcher(n);
        if(waWithText.matches()){
            String target=cleanTarget(waWithText.group(1));
            if(validTarget(target))return new Command("MESSAGE",target,recoverWhatsAppMessage(original,cleanMessage(waWithText.group(2))),"whatsapp");
        }

        Matcher waNoText=Pattern.compile("^(.+?) (?:e|a) whatsapp (?:tan|dan) (?:yaz|mesaj at|mesaj gonder)$").matcher(n);
        if(waNoText.matches()){
            String target=cleanTarget(waNoText.group(1));
            if(validTarget(target))return new Command("MESSAGE",target,"","whatsapp");
        }

        Matcher smsWithText=Pattern.compile("^(.+?) (?:e|a) (?:mesaj|sms) (?:gonder|at) (.+)$").matcher(n);
        if(smsWithText.matches()){
            String target=cleanTarget(smsWithText.group(1));
            if(validTarget(target))return new Command("MESSAGE",target,recoverSmsMessage(original,cleanMessage(smsWithText.group(2))),"sms");
        }

        Matcher smsNoText=Pattern.compile("^(.+?) (?:e|a) (?:mesaj|sms) (?:gonder|at)$").matcher(n);
        if(smsNoText.matches()){
            String target=cleanTarget(smsNoText.group(1));
            if(validTarget(target))return new Command("MESSAGE",target,"","sms");
        }

        Matcher call=Pattern.compile("^(.+?) ara$").matcher(n);
        if(call.matches()){
            String target=cleanTarget(call.group(1));
            if(validTarget(target)&&!target.matches(".*\\d.*")&&!reserved(target))
                return new Command("CALL",target,"","call");
        }

        return null;
    }

    static String recoverWhatsAppMessage(String original,String fallback){
        try{
            Matcher m=Pattern.compile("(?iu)^.+?['’]?[ea]\\s+whatsapp['’]?(?:tan|dan)\\s+(.+?)\\s+(?:yaz|gönder)$").matcher(original);
            if(m.matches())return m.group(1).trim();
        }catch(Exception ignored){}
        return fallback;
    }

    static String recoverContextWhatsAppMessage(String original,String fallback){
        try{
            Matcher m=Pattern.compile("(?iu)^(?:olmadı\\s+)?(?:ona\\s+)?whatsapp['’]?(?:tan|dan)\\s+(.+?)\\s+(?:yaz|gönder)$").matcher(original);
            if(m.matches())return m.group(1).trim();
        }catch(Exception ignored){}
        return fallback;
    }

    static String recoverSmsMessage(String original,String fallback){
        try{
            Matcher m=Pattern.compile("(?iu)^.+?['’]?[ea]\\s+(?:mesaj|sms)\\s+(?:gönder|at)\\s+(.+)$").matcher(original);
            if(m.matches())return m.group(1).trim();
        }catch(Exception ignored){}
        return fallback;
    }

    static String recoverContextSmsMessage(String original,String fallback){
        try{
            Matcher m=Pattern.compile("(?iu)^(?:ona\\s+)?(?:mesaj|sms)\\s+(?:gönder|at)\\s+(.+)$").matcher(original);
            if(m.matches())return m.group(1).trim();
        }catch(Exception ignored){}
        return fallback;
    }

    static String cleanTarget(String s){
        if(s==null)return "";
        String t=s.trim().replaceAll("\\s+"," ");
        t=t.replaceAll(" (?:i|yi|u|yu|e|a)$","");
        return t.trim();
    }

    static String cleanMessage(String s){
        if(s==null)return "";
        return s.trim().replaceAll("\\s+"," ");
    }

    static boolean validTarget(String s){
        return s!=null&&s.trim().length()>=2&&s.trim().length()<=80;
    }

    static boolean reserved(String s){
        String n=normalize(s);
        return n.matches(".*\\b(?:alarm|saat|wifi|wi fi|bluetooth|fener|flash|spotify|youtube|muzik|sarki|uygulama)\\b.*");
    }

    static boolean yes(String raw){
        String n=normalize(stripWake(raw));
        return eqAny(n,"evet","onayliyorum","onayla","tamam","gonder","gonderebilirsin","olur","evet gonder");
    }

    static boolean no(String raw){
        String n=normalize(stripWake(raw));
        return eqAny(n,"hayir","iptal","vazgectim","vazgec","gonderme","hayir gonderme");
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
