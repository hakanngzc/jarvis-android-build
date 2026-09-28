package com.hakan.jarvis;

public final class ConversationContextTest {
    private static int pass=0,fail=0;

    private static void expect(String input,String prev,long age,String intent){
        ConversationRouter.Reply r=ConversationRouter.matchContext(input,prev,"","",age);
        String got=r==null?null:r.intent;
        if(intent==null?got==null:intent.equals(got)) pass++;
        else {
            fail++;
            System.out.println("FAIL input="+input+" prev="+prev+" expected="+intent+" got="+got);
        }
    }

    public static void main(String[] args){
        expect("Jarvis","",0,"wake_exact");
        expect("Hey Jarvis","",0,"wake_exact");
        expect("Jarvis merhaba","",0,"greeting");
        expect("Jarvis nasılsın?","",0,"wellbeing");
        expect("iyiyim","wellbeing",15000,"wellbeing_positive_followup");
        expect("pek iyi değilim","wellbeing",15000,"wellbeing_negative_followup");
        expect("sen?","wellbeing",15000,"context_you");
        expect("tamam","activity",15000,"acknowledge");
        expect("tamam","activity",180000,null);
        expect("mesela","capabilities",10000,"capabilities_followup");
        expect("neden","identity",10000,"identity_followup");
        expect("beni duyuyor musun","",0,"hearing");
        expect("adın ne","",0,"identity");
        expect("neler yapabilirsin","",0,"capabilities");
        expect("görüşürüz","",0,"farewell");

        // Command shield regression: conversation must never hijack action commands.
        expect("Jarvis feneri aç","wellbeing",1000,null);
        expect("Jarvis Spotify aç","wellbeing",1000,null);
        expect("20 dakika sonra alarm kur","wellbeing",1000,null);
        expect("sesi yükselt","wellbeing",1000,null);
        expect("YouTube'u aç","wellbeing",1000,null);
        expect("not al bugün markete git","wellbeing",1000,null);

        System.out.println("ConversationContext: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
