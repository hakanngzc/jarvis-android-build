package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class SemanticCommandBrain {
    public static final String PROFILE="SEMANTIC_COMMAND_BRAIN_V1";
    public static final int AUTO_THRESHOLD=88;
    public static final int CONFIRM_THRESHOLD=70;

    public static final class Resolution {
        public final String intent;
        public final String canonicalCommand;
        public final int confidence;
        public final String reason;
        Resolution(String intent,String canonicalCommand,int confidence,String reason){
            this.intent=intent;
            this.canonicalCommand=canonicalCommand;
            this.confidence=confidence;
            this.reason=reason;
        }
        public boolean autoExecute(){return confidence>=AUTO_THRESHOLD;}
        public boolean needsConfirmation(){return confidence>=CONFIRM_THRESHOLD&&confidence<AUTO_THRESHOLD;}
    }

    private SemanticCommandBrain(){}

    public static Resolution resolve(String raw){
        String q=normalize(stripWake(raw));
        if(q.length()==0)return null;

        // Safety exclusions: timing, people, messaging, web questions and exact media search
        // remain owned by their dedicated deterministic engines.
        if(hasAny(q,"alarm","hatirlatici","hatirlat","dakika sonra","saat "))
            return null;
        if(hasAny(q,"whatsapp","mesaj gonder","mesaj at"," ara","ara ","telefon et","rehber"))
            return null;
        if(hasAny(q,"google","internetten","webde","youtube da ara","nedir","kimdir","ne zaman","kac "))
            return null;

        Resolution r;

        r=device(q,"bluetooth",
            new String[]{"bluetooth","blutut","blu tot"},
            "Bluetooth aç","Bluetooth kapat",
            "BLUETOOTH_ON","BLUETOOTH_OFF");
        if(r!=null)return r;

        r=device(q,"wifi",
            new String[]{"wifi","wi fi","kablosuz ag","kablosuz internet"},
            "Wi-Fi aç","Wi-Fi kapat",
            "WIFI_ON","WIFI_OFF");
        if(r!=null)return r;

        r=flash(q);
        if(r!=null)return r;

        r=volume(q);
        if(r!=null)return r;

        r=media(q);
        if(r!=null)return r;

        return null;
    }

    private static Resolution device(String q,String label,String[] anchors,
                                     String onCmd,String offCmd,String onIntent,String offIntent){
        boolean anchor=hasAny(q,anchors);
        if(!anchor)return null;

        int onScore=0,offScore=0;
        String reason="";

        if(hasAny(q,"aktif et","aktiflestir","etkinlestir","devreye al","ac","calistir")){
            onScore=96;reason=label+" + etkinleştirme ifadesi";
        }else if(hasAny(q,"lazim","gerekli","ihtiyacim var","kullanacagim")){
            onScore=89;reason=label+" + ihtiyaç bağlamı";
        }

        if(hasAny(q,"pasif et","pasiflestir","devre disi birak","devreden cikar","kapat","sonlandir")){
            offScore=96;reason=label+" + kapatma ifadesi";
        }else if(hasAny(q,"gerekmiyor","lazim degil","ihtiyacim yok","kullanmayacagim")){
            offScore=90;reason=label+" + ihtiyaç yok bağlamı";
        }

        if(onScore==0&&offScore==0){
            if(q.length()<=18)
                return new Resolution(onIntent,onCmd,72,label+" adı var fakat eylem belirsiz");
            return null;
        }
        if(onScore>0&&offScore>0)return null;
        if(onScore>0)return new Resolution(onIntent,onCmd,onScore,reason);
        return new Resolution(offIntent,offCmd,offScore,reason);
    }

    private static Resolution flash(String q){
        boolean anchor=hasAny(q,"fener","flash","flas","isigi","isik");
        if(!anchor)return null;
        if(hasAny(q,"ac","yak","aktif et","devreye al"))
            return new Resolution("FLASH_ON","feneri aç",hasAny(q,"fener","flash","flas")?95:82,"ışık/fener + açma");
        if(hasAny(q,"kapat","sondur","pasif et","devreden cikar"))
            return new Resolution("FLASH_OFF","feneri kapat",hasAny(q,"fener","flash","flas")?95:82,"ışık/fener + kapatma");
        return null;
    }

    private static Resolution volume(String q){
        boolean anchor=hasAny(q,"ses","sesi","volume");
        if(!anchor)return null;
        if(hasAny(q,"arttir","yukselt","ac biraz","daha yuksek","sesli yap"))
            return new Resolution("VOLUME_UP","sesi yükselt",94,"ses + artırma");
        if(hasAny(q,"azalt","kis","dusur","daha sessiz","sessiz yap"))
            return new Resolution("VOLUME_DOWN","sesi kıs",94,"ses + azaltma");
        return null;
    }

    private static Resolution media(String q){
        boolean music=hasAny(q,"muzik","sarki","parca","oynatma","spotify");
        if(hasAny(q,"duraklat","beklet","biraz beklet","muzigi durdur","sarkiyi durdur","oynatmayi durdur")){
            return new Resolution("MEDIA_PAUSE","müziği durdur",music?95:78,music?"medya + duraklatma":"duraklatma ifadesi");
        }
        if(hasAny(q,"surdur","devam ettir","kaldigi yerden surdur","kaldigi yerden oynat","muzige devam")){
            return new Resolution("MEDIA_RESUME","devam et",music?95:80,music?"medya + devam":"devam ifadesi");
        }
        if(hasAny(q,"obur sarki","diger sarki","siradaki sarki","ilerideki parca","bir sonrakini ac")){
            return new Resolution("MEDIA_NEXT","sonraki",96,"sonraki medya ifadesi");
        }
        if(hasAny(q,"onceki sarki","bir onceki parca","geri onceki","oncekini ac")){
            return new Resolution("MEDIA_PREVIOUS","önceki",96,"önceki medya ifadesi");
        }

        // Very short ambiguous action: ask rather than execute.
        if(q.equals("duraklat")||q.equals("beklet"))
            return new Resolution("MEDIA_PAUSE","müziği durdur",74,"kısa ve bağlamsız duraklatma");
        if(q.equals("surdur"))
            return new Resolution("MEDIA_RESUME","devam et",74,"kısa ve bağlamsız devam");

        return null;
    }

    public static boolean yes(String raw){
        String q=normalize(stripWake(raw));
        return eqAny(q,"evet","aynen","dogru","tamam","onay","onayliyorum","yap","evet yap");
    }

    public static boolean no(String raw){
        String q=normalize(stripWake(raw));
        return eqAny(q,"hayir","yok","iptal","vazgec","yapma","yanlis");
    }

    public static String confirmationText(Resolution r){
        if(r==null)return "";
        String action;
        if("BLUETOOTH_ON".equals(r.intent))action="Bluetooth'u açmamı";
        else if("BLUETOOTH_OFF".equals(r.intent))action="Bluetooth'u kapatmamı";
        else if("WIFI_ON".equals(r.intent))action="Wi-Fi'yi açmamı";
        else if("WIFI_OFF".equals(r.intent))action="Wi-Fi'yi kapatmamı";
        else if("FLASH_ON".equals(r.intent))action="feneri açmamı";
        else if("FLASH_OFF".equals(r.intent))action="feneri kapatmamı";
        else if("VOLUME_UP".equals(r.intent))action="sesi yükseltmemi";
        else if("VOLUME_DOWN".equals(r.intent))action="sesi kısmamı";
        else if("MEDIA_PAUSE".equals(r.intent))action="müziği durdurmamı";
        else if("MEDIA_RESUME".equals(r.intent))action="müziğe devam etmemi";
        else if("MEDIA_NEXT".equals(r.intent))action="sonraki parçaya geçmemi";
        else if("MEDIA_PREVIOUS".equals(r.intent))action="önceki parçaya dönmemi";
        else action="bu işlemi yapmamı";
        return action+" mı istiyorsunuz efendim?";
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

    static boolean hasAny(String s,String... values){
        for(String v:values)if(s.contains(v))return true;
        return false;
    }

    static boolean eqAny(String s,String... values){
        for(String v:values)if(s.equals(v))return true;
        return false;
    }
}
