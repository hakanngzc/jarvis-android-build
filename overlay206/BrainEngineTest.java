package com.hakan.jarvis;

public final class BrainEngineTest {
    private static int pass=0,fail=0;

    private static void check(String input,String intent,String action,String routedContains,int minConfidence){
        BrainEngine.Result r=BrainEngine.analyze(input);
        boolean ok=intent.equals(r.intent)
            && (action.length()==0||action.equals(r.action))
            && (routedContains.length()==0||BrainEngine.normalize(r.routedCommand).contains(BrainEngine.normalize(routedContains)))
            && r.confidence>=minConfidence;
        if(ok)pass++;
        else{
            fail++;
            System.out.println("FAIL input="+input+" intent="+r.intent+" action="+r.action+" routed="+r.routedCommand+" conf="+r.confidence);
        }
    }

    public static void main(String[] args){
        check("blutut aç","DEVICE_CONTROL","BLUETOOTH_ON","bluetooth",90);
        check("bluetooth lazım","DEVICE_CONTROL","BLUETOOTH_ON","bluetooth aç",80);
        check("bt yi kapat","DEVICE_CONTROL","BLUETOOTH_OFF","bluetooth kapat",90);
        check("vayfay aktif et","DEVICE_CONTROL","WIFI_ON","wifi aç",90);
        check("wi fi kapat","DEVICE_CONTROL","WIFI_OFF","wifi kapat",90);

        check("müziği kes","MEDIA","PAUSE","durdur",90);
        check("kaldığı yerden devam","MEDIA","RESUME","devam",90);
        check("sonraki parçaya geç","MEDIA","NEXT","sonrakine",90);
        check("bir önceki parçaya dön","MEDIA","PREVIOUS","öncekine",90);

        check("spotifay aç","APP","OPEN_PROVIDER","spotify aç",90);
        check("20 dk sonra alaram kur","ALARM","SET_RELATIVE","20 dakika sonra alarm kur",95);
        check("Biraderimi ara","CONTACT_CALL","CALL","",85);
        check("İkbal'e WhatsApp'tan merhaba nasılsın yaz","CONTACT_MESSAGE","MESSAGE","",85);

        BrainEngine.Result msg=BrainEngine.analyze("İkbal'e WhatsApp'tan spotifay çok iyi yaz");
        if(msg.protectedFreeText && !msg.rewritten && msg.routedCommand.contains("spotifay"))pass++;
        else{fail++;System.out.println("FAIL protected message="+msg.routedCommand);}

        BrainEngine.Result unknown=BrainEngine.analyze("bugün nasılsın");
        if("UNKNOWN".equals(unknown.intent)&&unknown.confidence<50&&!unknown.rewritten)pass++;
        else{fail++;System.out.println("FAIL unknown="+unknown.intent+" "+unknown.confidence);}

        if(BrainEngine.levenshtein("bluetooth","blutut")<=4)pass++; else fail++;
        if(BrainEngine.hybridSimilarity("wifi ac","wifi ac")>.99)pass++; else fail++;

        System.out.println("BrainEngine: PASS "+pass+" / FAIL "+fail);
        if(fail>0)System.exit(1);
    }
}
