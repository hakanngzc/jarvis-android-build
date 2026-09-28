package com.hakan.jarvis;

public final class ConversationMemoryTest {
    private static int pass=0, fail=0;

    private static ConversationRouter.Reply r(String input,String prev,long age,String name,String topic){
        return ConversationRouter.matchContext(input,prev,"","",age,name,topic);
    }
    private static void intent(String input,String prev,long age,String name,String topic,String expected){
        ConversationRouter.Reply x=r(input,prev,age,name,topic);
        String got=x==null?null:x.intent;
        if(expected==null?got==null:expected.equals(got))pass++;
        else{fail++;System.out.println("FAIL "+input+" expected="+expected+" got="+got);}
    }
    private static void memName(String input,String expected){
        ConversationRouter.Reply x=r(input,"",0,"","");
        String got=x==null?null:x.memoryName;
        if(expected==null?got==null:expected.equals(got))pass++;
        else{fail++;System.out.println("FAIL name "+input+" expected="+expected+" got="+got);}
    }
    private static void memTopic(String input,String expected){
        ConversationRouter.Reply x=r(input,"",0,"","");
        String got=x==null?null:x.memoryTopic;
        if(expected==null?got==null:expected.equals(got))pass++;
        else{fail++;System.out.println("FAIL topic "+input+" expected="+expected+" got="+got);}
    }

    public static void main(String[] args){
        intent("adım Hakan","",0,"","", "memory_name_store");
        memName("adım hakan","Hakan");
        intent("benim adım ne","",0,"Hakan","", "memory_name_recall");
        intent("ben kimim","",0,"Hakan","", "memory_name_recall");
        intent("ismimi unut","",0,"Hakan","", "memory_name_clear");

        intent("futbol hakkında konuşalım","",0,"","", "memory_topic_store");
        memTopic("futbol hakkında konuşalım","Futbol");
        intent("ne hakkında konuşuyorduk","",0,"","Futbol", "memory_topic_recall");
        intent("devam edelim","",10000,"","Futbol", "topic_continue");
        intent("konuyu kapat","",0,"","Futbol", "memory_topic_clear");

        intent("gerçekten mi","activity",1000,"","", "context_confirm");
        intent("harika","activity",1000,"","", "acknowledge");
        intent("harika","activity",240000,"","", null);

        // Command shield remains authoritative.
        intent("Jarvis feneri aç","wellbeing",1000,"Hakan","Futbol",null);
        intent("20 dakika sonra alarm kur","wellbeing",1000,"Hakan","Futbol",null);
        intent("Spotify aç","wellbeing",1000,"Hakan","Futbol",null);
        intent("sesi yükselt","wellbeing",1000,"Hakan","Futbol",null);

        System.out.println("ConversationMemory: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
