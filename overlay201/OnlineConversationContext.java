package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class OnlineConversationContext {
    public static final String PROFILE="ONLINE_CONTEXT_V2";
    public static final long WINDOW_MS=180000L;

    private OnlineConversationContext(){}

    public static String resolve(String raw,String lastTopic,long ageMs){
        if(raw==null||lastTopic==null||ageMs<0||ageMs>WINDOW_MS)return null;
        String topic=lastTopic.trim();
        if(topic.length()<2)return null;
        String q=normalize(OnlineQueryRouter.query(raw));
        if(q.length()==0)return null;

        if(eq(q,"biraz daha anlat","daha fazla anlat","devam et","devamini anlat","biraz daha bilgi ver"))
            return topic+" hakkında biraz daha anlat";

        if(eq(q,"ne zaman dogdu","ne zaman dogmus","dogum tarihi ne","hangi yil dogdu"))
            return topic+" ne zaman doğdu";

        if(eq(q,"nereli","nereliydi","nerede dogdu","nerede dogmus"))
            return topic+" nerede doğdu";

        if(eq(q,"ne zaman oldu","ne zaman gerceklesti","hangi yil oldu"))
            return topic+" ne zaman oldu";

        if(eq(q,"ne zaman kuruldu","hangi yil kuruldu"))
            return topic+" ne zaman kuruldu";

        if(eq(q,"neden","neden peki","peki neden"))
            return topic+" neden";

        if(eq(q,"nasil","nasil peki","peki nasil"))
            return topic+" nasıl";

        if(eq(q,"ne demek","bu ne demek"))
            return topic+" ne demek";

        if(eq(q,"peki nereli","peki nereliydi","peki nerede dogdu","peki nerede dogmus"))
            return topic+" nerede doğdu";

        if(q.startsWith("peki ")){
            String tail=q.substring(5).trim();
            if(tail.length()>=3 && isSafeFollowup(tail))return topic+" "+tail;
        }
        return null;
    }

    public static String topicFromAnswer(String requestedQuery,String answerTitle){
        String title=answerTitle==null?"":answerTitle.trim();
        if(title.length()>=2&&title.length()<=100)return title;
        String q=OnlineQueryRouter.searchTerms(requestedQuery);
        return q.length()>100?q.substring(0,100).trim():q;
    }

    private static boolean isSafeFollowup(String q){
        if(OnlineQueryRouter.looksLikeDeviceAction(q)||OnlineQueryRouter.looksRealtimeUnsupported(q))return false;
        return q.startsWith("ne ")||q.startsWith("neden")||q.startsWith("nasil")||
               q.startsWith("nerede")||q.startsWith("hangi ")||q.startsWith("kac ")||
               q.startsWith("kim ")||q.contains("hakkinda");
    }

    static boolean eq(String s,String...v){for(String x:v)if(s.equals(x))return true;return false;}

    static String normalize(String raw){
        if(raw==null)return "";
        String s=raw.trim().toLowerCase(new Locale("tr","TR"));
        s=s.replace('ı','i').replace('ğ','g').replace('ü','u').replace('ş','s').replace('ö','o').replace('ç','c');
        s=Normalizer.normalize(s,Normalizer.Form.NFD).replaceAll("\\p{M}+","");
        s=s.replace('’',' ').replace('\'',' ');
        return s.replaceAll("[^a-z0-9 ]+"," ").replaceAll("\\s+"," ").trim();
    }
}
