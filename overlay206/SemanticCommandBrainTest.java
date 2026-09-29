package com.hakan.jarvis;

public final class SemanticCommandBrainTest {
    private static int pass=0,fail=0;

    private static void expect(String raw,String intent,int min,int max){
        SemanticCommandBrain.Resolution r=SemanticCommandBrain.resolve(raw);
        boolean ok=r!=null&&intent.equals(r.intent)&&r.confidence>=min&&r.confidence<=max;
        if(ok)pass++; else{fail++;System.out.println("FAIL resolve: "+raw+" => "+(r==null?"null":r.intent+"/"+r.confidence+"/"+r.canonicalCommand));}
    }

    private static void none(String raw){
        SemanticCommandBrain.Resolution r=SemanticCommandBrain.resolve(raw);
        if(r==null)pass++; else{fail++;System.out.println("FAIL expected null: "+raw+" => "+r.intent+"/"+r.confidence);}
    }

    private static void truth(boolean v,String name){
        if(v)pass++; else{fail++;System.out.println("FAIL "+name);}
    }

    public static void main(String[] args){
        expect("Bluetooth'u aktif et","BLUETOOTH_ON",88,100);
        expect("kulaklığı bağlayacağım bluetooth lazım","BLUETOOTH_ON",88,100);
        expect("bluetoothu devreye al","BLUETOOTH_ON",88,100);
        expect("bluetooth artık gerekmiyor","BLUETOOTH_OFF",88,100);
        expect("bluetoothu devreden çıkar","BLUETOOTH_OFF",88,100);
        expect("blutut kapansın","BLUETOOTH_OFF",88,100);

        expect("wi fi aktif et","WIFI_ON",88,100);
        expect("kablosuz internet lazım","WIFI_ON",88,100);
        expect("wifi artık gerekmiyor","WIFI_OFF",88,100);
        expect("kablosuz ağı devreden çıkar","WIFI_OFF",88,100);

        expect("feneri yak","FLASH_ON",88,100);
        expect("flashı devreye al","FLASH_ON",88,100);
        expect("ışığı aç","FLASH_ON",70,87);
        expect("feneri söndür","FLASH_OFF",88,100);

        expect("sesi biraz yükselt","VOLUME_UP",88,100);
        expect("daha sessiz yap sesi","VOLUME_DOWN",88,100);

        expect("müziği biraz beklet","MEDIA_PAUSE",88,100);
        expect("şarkıyı duraklat","MEDIA_PAUSE",88,100);
        expect("duraklat","MEDIA_PAUSE",70,87);
        expect("müziği kaldığı yerden sürdür","MEDIA_RESUME",88,100);
        expect("sürdür","MEDIA_RESUME",70,87);
        expect("öbür şarkıya geç","MEDIA_NEXT",88,100);
        expect("bir önceki parçayı aç","MEDIA_PREVIOUS",88,100);

        none("20 dakika sonra alarm kur");
        none("saat 8'e alarm kur");
        none("Ahmet'i ara");
        none("İkbal'e WhatsApp'tan merhaba yaz");
        none("Google'da Beşiktaş ara");
        none("kara delik nedir");
        none("Müslüm Gürses Nilüfer çal");
        none("bağlantıyı aç");
        none("yarın hava nasıl");

        truth(SemanticCommandBrain.yes("evet"),"yes evet");
        truth(SemanticCommandBrain.yes("aynen"),"yes aynen");
        truth(SemanticCommandBrain.no("hayır"),"no hayir");
        truth(SemanticCommandBrain.no("vazgeç"),"no vazgec");

        SemanticCommandBrain.Resolution medium=SemanticCommandBrain.resolve("duraklat");
        truth(medium!=null&&medium.needsConfirmation()&&!medium.autoExecute(),"medium threshold");
        SemanticCommandBrain.Resolution high=SemanticCommandBrain.resolve("Bluetooth'u aktif et");
        truth(high!=null&&high.autoExecute(),"high threshold");

        System.out.println("SemanticCommandBrain: PASS "+pass+" / FAIL "+fail);
        if(fail>0)System.exit(1);
    }
}
