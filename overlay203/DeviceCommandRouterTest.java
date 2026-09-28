package com.hakan.jarvis;

public final class DeviceCommandRouterTest {
    static int pass=0,fail=0;

    static void expect(String raw,String action){
        DeviceCommandRouter.Command c=DeviceCommandRouter.parse(raw);
        boolean ok=c!=null&&action.equals(c.action);
        if(ok)pass++;else{fail++;System.out.println("FAIL "+raw+" -> "+(c==null?"null":c.action));}
    }

    static void reject(String raw){
        DeviceCommandRouter.Command c=DeviceCommandRouter.parse(raw);
        if(c==null)pass++;else{fail++;System.out.println("FAIL reject "+raw+" -> "+c.action);}
    }

    public static void main(String[]args){
        expect("Bluetooth'u aç","BLUETOOTH_ON");
        expect("bluetooth aç","BLUETOOTH_ON");
        expect("Hey Jarvis bluetoothu aç","BLUETOOTH_ON");
        expect("Bluetooth'u açar mısın","BLUETOOTH_ON");
        expect("aç bluetooth","BLUETOOTH_ON");
        expect("Bluetooth'u kapat","BLUETOOTH_OFF");
        expect("Bluetooth kapat","BLUETOOTH_OFF");
        expect("Hey Jarvis bluetoothu kapat","BLUETOOTH_OFF");
        expect("kapat bluetooth","BLUETOOTH_OFF");

        expect("Wi-Fi'yi aç","WIFI_ON");
        expect("wifi aç","WIFI_ON");
        expect("wi fi aç","WIFI_ON");
        expect("Hey Jarvis wifiyi aç","WIFI_ON");
        expect("aç wifi","WIFI_ON");
        expect("kablosuz ağı aç","WIFI_ON");
        expect("Wi-Fi'yi kapat","WIFI_OFF");
        expect("wifi kapat","WIFI_OFF");
        expect("wi fi kapat","WIFI_OFF");
        expect("kapat wifi","WIFI_OFF");
        expect("kablosuz ağı kapat","WIFI_OFF");

        reject("Bluetooth açık mı");
        reject("Wi-Fi açık mı");
        reject("wifi durumu ne");
        reject("Spotify aç");
        reject("YouTube'u aç");
        reject("interneti aç");
        reject("feneri aç");
        reject("alarm kur");

        System.out.println("DeviceCommandRouter: PASS "+pass+" / FAIL "+fail);
        if(fail!=0)System.exit(1);
    }
}
