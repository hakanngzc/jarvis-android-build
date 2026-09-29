package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class BrainEngine {
    public static final String PROFILE="BRAIN_ENGINE_V1";
    public static final String ASR_PROFILE="ASR_CORRECTION_V1";
    public static final String ENTITY_PROFILE="TURKISH_ENTITY_V2";
    public static final String CONFIDENCE_PROFILE="CONFIDENCE_ENGINE_V1";
    public static final String FALLBACK_PROFILE="LOCAL_INTENT_SIMILARITY_V1";

    public static final class Result {
        public final String original;
        public final String normalized;
        public final String corrected;
        public final String routedCommand;
        public final String intent;
        public final String action;
        public final String target;
        public final String provider;
        public final int confidence;
        public final boolean rewritten;
        public final boolean protectedFreeText;

        Result(String original,String normalized,String corrected,String routedCommand,
               String intent,String action,String target,String provider,int confidence,
               boolean rewritten,boolean protectedFreeText){
            this.original=original==null?"":original;
            this.normalized=normalized==null?"":normalized;
            this.corrected=corrected==null?"":corrected;
            this.routedCommand=routedCommand==null?this.original:routedCommand;
            this.intent=intent==null?"UNKNOWN":intent;
            this.action=action==null?"":action;
            this.target=target==null?"":target;
            this.provider=provider==null?"":provider;
            this.confidence=Math.max(0,Math.min(100,confidence));
            this.rewritten=rewritten;
            this.protectedFreeText=protectedFreeText;
        }
    }

    private static final class Candidate {
        final String intent,action,command;
        final int score;
        Candidate(String intent,String action,String command,int score){
            this.intent=intent;this.action=action;this.command=command;this.score=score;
        }
    }

    private BrainEngine(){}

    public static Result analyze(String raw){
        String original=raw==null?"":raw.trim();
        if(original.length()==0)
            return new Result(original,"","","","UNKNOWN","","","",0,false,false);

        String noWake=stripWakeRaw(original);
        String normalized=normalize(noWake);
        boolean freeText=looksProtectedFreeText(normalized);

        String corrected=correctAsr(normalized);
        Entity entity=extractEntities(corrected);

        Candidate direct=classifyDirect(corrected,entity);
        Candidate fallback=direct==null&&!freeText?similarityFallback(corrected):null;
        Candidate best=direct!=null?direct:fallback;

        if(best==null){
            return new Result(original,normalized,corrected,original,
                    inferBroadIntent(corrected),"",entity.target,entity.provider,
                    broadConfidence(corrected),false,freeText);
        }

        boolean correctionChanged=!corrected.equals(normalized);
        boolean canonicalChanged=!best.command.equals(corrected);
        boolean safe=!freeText && best.score>=80 && (correctionChanged||canonicalChanged);
        String routed=safe?best.command:original;
        return new Result(original,normalized,corrected,routed,best.intent,best.action,
                entity.target,entity.provider,best.score,safe,freeText);
    }

    private static Candidate classifyDirect(String n,Entity e){
        if(n.length()==0)return null;

        if(hasAny(n,"bluetooth","blutut","bt")){
            if(hasOnVerb(n)||containsAny(n,"bluetooth lazim","bluetooth gerekli","bt lazim"))
                return new Candidate("DEVICE_CONTROL","BLUETOOTH_ON","bluetooth aç",96);
            if(hasOffVerb(n))
                return new Candidate("DEVICE_CONTROL","BLUETOOTH_OFF","bluetooth kapat",96);
        }

        if(hasAny(n,"wifi","wi fi","vayfay","kablosuz ag","kablosuz")){
            if(hasOnVerb(n)||containsAny(n,"wifi lazim","kablosuz lazim"))
                return new Candidate("DEVICE_CONTROL","WIFI_ON","wifi aç",95);
            if(hasOffVerb(n))
                return new Candidate("DEVICE_CONTROL","WIFI_OFF","wifi kapat",95);
        }

        if(containsAny(n,"muzigi kes","sarkiyi kes","muzigi sustur","sarkiyi sustur"))
            return new Candidate("MEDIA","PAUSE","müziği durdur",93);
        if(eqAny(n,"devam","devam et","muzige devam","sarkiya devam","kaldigi yerden devam"))
            return new Candidate("MEDIA","RESUME","devam et",98);
        if(containsAny(n,"sonraki parcaya","sonraki sarkiya","siradakine"))
            return new Candidate("MEDIA","NEXT","sonrakine geç",97);
        if(containsAny(n,"onceki parcaya","onceki sarkiya","bir oncekine"))
            return new Candidate("MEDIA","PREVIOUS","öncekine dön",97);

        if(e.provider.length()>0 && containsAny(n,"ac","baslat","calistir") && !containsAny(n,"cal ","oynat","sarki","muzik"))
            return new Candidate("APP","OPEN_PROVIDER",e.provider+" aç",94);

        String naturalApp=findNaturalApp(n);
        if(naturalApp.length()>0){
            if(containsAny(n,"lazim","girecegim","kullanacagim","acmak istiyorum","baslatmak istiyorum"))
                return new Candidate("APP","OPEN",naturalApp+" aç",90);
            if(containsAny(n,"kapat","cikmak istiyorum","sonlandir"))
                return new Candidate("APP","CLOSE",naturalApp+" kapat",92);
        }

        if(containsAny(n,"yarim saat sonra") && containsAny(n,"uyandir","alarm")){
            return new Candidate("ALARM","SET_RELATIVE","30 dakika sonra alarm kur",99);
        }

        Matcher rel=Pattern.compile(".*?(\\d{1,4})\\s*(?:dakika|dk)\\s*sonra.*?(?:alarm|uyandir).*").matcher(n);
        if(rel.matches()){
            int min=Integer.parseInt(rel.group(1));
            if(min>=1&&min<=1440)
                return new Candidate("ALARM","SET_RELATIVE",min+" dakika sonra alarm kur",99);
        }

        Matcher relHour=Pattern.compile(".*?(\\d{1,2})\\s*saat\\s*sonra.*?(?:alarm|uyandir).*").matcher(n);
        if(relHour.matches()){
            int hour=Integer.parseInt(relHour.group(1));
            int min=hour*60;
            if(hour>=1&&hour<=24)
                return new Candidate("ALARM","SET_RELATIVE",min+" dakika sonra alarm kur",99);
        }

        if(n.matches(".*\\b(?:alarm|alaram|uyandir)\\b.*"))
            return new Candidate("ALARM","ALARM_COMMAND",n,86);

        if(n.matches("^.+\\s+ara$")&&!n.matches(".*\\d.*"))
            return new Candidate("CONTACT_CALL","CALL",n,91);

        if(containsAny(n,"whatsapp","mesaj gonder","mesaj at","sms gonder","sms at"))
            return new Candidate("CONTACT_MESSAGE","MESSAGE",n,93);

        if(containsAny(n,"spotify","youtube","muzik","sarki","cal","oynat"))
            return new Candidate("MEDIA","MEDIA_COMMAND",n,84);

        if(n.matches("^(?:ac|baslat|calistir) .+$")||n.matches("^.+ (?:ac|baslat|calistir)$"))
            return new Candidate("APP","OPEN",n,82);

        return null;
    }

    private static Candidate similarityFallback(String n){
        final String[][] prototypes={
            {"DEVICE_CONTROL","BLUETOOTH_ON","bluetooth aç"},
            {"DEVICE_CONTROL","BLUETOOTH_OFF","bluetooth kapat"},
            {"DEVICE_CONTROL","WIFI_ON","wifi aç"},
            {"DEVICE_CONTROL","WIFI_OFF","wifi kapat"},
            {"MEDIA","PAUSE","müziği durdur"},
            {"MEDIA","RESUME","devam et"},
            {"MEDIA","NEXT","sonrakine geç"},
            {"MEDIA","PREVIOUS","öncekine dön"},
            {"APP","OPEN","uygulamayı aç"}
        };

        Candidate best=null;
        for(String[] p:prototypes){
            String pn=normalize(p[2]);
            double sim=hybridSimilarity(n,pn);
            int score=(int)Math.round(sim*100.0);
            if(best==null||score>best.score)best=new Candidate(p[0],p[1],p[2],score);
        }
        if(best!=null&&best.score>=80)return best;
        return null;
    }

    static double hybridSimilarity(String a,String b){
        if(a.equals(b))return 1.0;
        double token=jaccard(a,b);
        double edit=1.0-((double)levenshtein(a,b)/(double)Math.max(1,Math.max(a.length(),b.length())));
        double score=.58*token+.42*edit;
        if(score<0)score=0;
        if(score>1)score=1;
        return score;
    }

    private static double jaccard(String a,String b){
        String[] aa=a.split(" "),bb=b.split(" ");
        int inter=0,union=0;
        java.util.HashSet<String> set=new java.util.HashSet<String>();
        for(String x:aa)if(x.length()>0)set.add(x);
        union=set.size();
        for(String x:bb){
            if(x.length()==0)continue;
            if(set.contains(x))inter++;
            else union++;
        }
        return union==0?0:(double)inter/(double)union;
    }

    static int levenshtein(String a,String b){
        int[] prev=new int[b.length()+1],cur=new int[b.length()+1];
        for(int j=0;j<=b.length();j++)prev[j]=j;
        for(int i=1;i<=a.length();i++){
            cur[0]=i;
            for(int j=1;j<=b.length();j++){
                int cost=a.charAt(i-1)==b.charAt(j-1)?0:1;
                cur[j]=Math.min(Math.min(cur[j-1]+1,prev[j]+1),prev[j-1]+cost);
            }
            int[] t=prev;prev=cur;cur=t;
        }
        return prev[b.length()];
    }

    private static final class Entity{
        String provider="";
        String target="";
        int minutes=-1;
    }

    private static String findNaturalApp(String n){
        String[][] apps={
            {"instagram","instagram","insta"},
            {"whatsapp","whatsapp","vatsap","watsap"},
            {"telegram","telegram"},
            {"spotify","spotify","spotifay"},
            {"youtube","youtube","yutub"},
            {"chrome","chrome","krom"},
            {"kamera","kamera","camera"},
            {"galeri","galeri","gallery"},
            {"ayarlar","ayarlar"},
            {"kişiler","kisiler","rehber"}
        };
        for(String[] row:apps){
            for(int i=1;i<row.length;i++){
                if((" "+n+" ").contains(" "+row[i]+" "))return row[0];
            }
        }
        return "";
    }

    private static Entity extractEntities(String n){
        Entity e=new Entity();
        if(containsAny(n,"spotify","spotif"))e.provider="spotify";
        else if(containsAny(n,"youtube music","youtube muzik"))e.provider="youtube music";
        else if(containsAny(n,"youtube","yutub"))e.provider="youtube";

        Matcher m=Pattern.compile("(\\d{1,4})\\s*(?:dakika|dk)\\s*sonra").matcher(n);
        if(m.find()){
            try{e.minutes=Integer.parseInt(m.group(1));}catch(Exception ignored){}
        }

        Matcher call=Pattern.compile("^(.+?)\\s+ara$").matcher(n);
        if(call.matches())e.target=call.group(1).trim();

        return e;
    }

    static String correctAsr(String raw){
        String s=raw==null?"":raw;
        s=s.replaceAll("\\b(?:blu tut|blue tooth|blutut|blututh|bluetoothh|bt yi|bt yi)\\b","bluetooth");
        s=s.replaceAll("\\b(?:vayfay|wayfay|wi fi|wifii|wifi yi|wifi yi)\\b","wifi");
        s=s.replaceAll("\\b(?:spotifay|spotifai|spotifiy|spotif)\\b","spotify");
        s=s.replaceAll("\\b(?:you tube|yutub|youtub)\\b","youtube");
        s=s.replaceAll("\\b(?:alaram|alarmm)\\b","alarm");
        s=s.replaceAll("\\b(?:vatsap|watsap|vat sap)\\b","whatsapp");
        s=s.replaceAll("\\b(?:insta gram)\\b","instagram");
        s=s.replaceAll("\\b(?:krom)\\b","chrome");
        s=s.replaceAll("\\b(?:aktiflestir|aktiflestir)\\b","aktif et");
        s=s.replaceAll("\\s+"," ").trim();
        return s;
    }

    private static boolean looksProtectedFreeText(String n){
        if(n==null)return false;
        if(n.contains("whatsapp")){
            String[] p=n.split(" ");
            return p.length>=5 && (n.contains(" yaz")||n.contains(" gonder"));
        }
        if(n.matches("^.+? (?:e|a) (?:mesaj|sms) (?:gonder|at) .+"))return true;
        return false;
    }

    private static String inferBroadIntent(String n){
        if(hasAny(n,"bluetooth","wifi","wi fi","kablosuz"))return "DEVICE_CONTROL";
        if(hasAny(n,"spotify","youtube","muzik","sarki","cal","oynat"))return "MEDIA";
        if(n.contains("alarm"))return "ALARM";
        if(n.endsWith(" ara"))return "CONTACT_CALL";
        if(hasAny(n,"whatsapp","mesaj","sms"))return "CONTACT_MESSAGE";
        return "UNKNOWN";
    }

    private static int broadConfidence(String n){
        String i=inferBroadIntent(n);
        return "UNKNOWN".equals(i)?25:62;
    }

    private static boolean hasOnVerb(String n){
        return containsAny(n," ac","ac ","aktif et","aktif olsun","devreye al","baslat")
            || n.endsWith(" ac")||n.startsWith("ac ");
    }

    private static boolean hasOffVerb(String n){
        return containsAny(n,"kapat","devre disi","pasif et","kapa");
    }

    private static boolean hasAny(String s,String... xs){return containsAny(s,xs);}
    private static boolean containsAny(String s,String... xs){
        for(String x:xs)if(s.contains(x))return true;
        return false;
    }
    private static boolean eqAny(String s,String... xs){
        for(String x:xs)if(s.equals(x))return true;
        return false;
    }

    static String stripWakeRaw(String raw){
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
