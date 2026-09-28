package com.hakan.jarvis;

public final class ConversationRouterTest {
    private static int pass=0,fail=0;

    private static void expect(String input,String intent){
        ConversationRouter.Reply r=ConversationRouter.match(input);
        String got=r==null?null:r.intent;
        if(intent==null?got==null:intent.equals(got)){
            pass++;
        }else{
            fail++;
            System.out.println("FAIL input="+input+" expected="+intent+" got="+got);
        }
    }

    public static void main(String[] args){
        expect("Jarvis","wake_exact");
        expect("Hey Jarvis","wake_exact");
        expect("Jarvis merhaba","greeting");
        expect("selam","greeting");
        expect("Günaydın","greeting");
        expect("Jarvis nasılsın?","wellbeing");
        expect("iyi misin","wellbeing");
        expect("Jarvis ne yapıyorsun","activity");
        expect("Jarvis sen kimsin","identity");
        expect("teşekkür ederim","thanks");
        expect("Jarvis hazır mısın","ready");
        expect("Jarvis feneri aç",null);
        expect("Jarvis Spotify aç",null);
        expect("20 dakika sonra alarm kur",null);
        expect("ben jarvis değilim",null);
        expect("sesi yükselt",null);
        System.out.println("ConversationRouter: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
