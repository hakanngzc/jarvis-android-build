package com.hakan.jarvis;

import java.text.Normalizer;
import java.util.Locale;

public final class DeviceCommandRouter {
    public static final String PROFILE="DEVICE_CONTROL_V1";

    public static final class Command {
        public final String action;
        public final String reply;
        public Command(String action,String reply){
            this.action=action;
            this.reply=reply;
        }
    }

    private DeviceCommandRouter(){}

    public static Command parse(String raw){
        String n=normalize(stripWake(raw));
        if(n.length()==0)return null;

        // Status questions are intentionally NOT part of 2.0.3.
        if(n.matches(".*\\b(?:acik mi|kapali mi|durumu ne|acikmi|kapalimi)\\b.*"))return null;

        if(matchesBluetooth(n,"ac"))
            return new Command("BLUETOOTH_ON","Bluetooth'u açıyorum efendim.");
        if(matchesBluetooth(n,"kapat"))
            return new Command("BLUETOOTH_OFF","Bluetooth'u kapatıyorum efendim.");

        if(matchesWifi(n,"ac"))
            return new Command("WIFI_ON","Wi-Fi'yi açıyorum efendim.");
        if(matchesWifi(n,"kapat"))
            return new Command("WIFI_OFF","Wi-Fi'yi kapatıyorum efendim.");

        return null;
    }

    static boolean matchesBluetooth(String n,String verb){
        return n.matches("^(?:lutfen )?(?:bluetooth|blutut|blu tot|bluetoothu|bluetooth u|bluetooth i|bluetooth yi|blututu) "
                +verb+"(?:ar misin|er misin|abilir misin|abilir misiniz|iver|iver misin)?$")
            || n.matches("^(?:lutfen )?"+verb+" (?:bluetooth|blutut|bluetoothu|blututu)$");
    }

    static boolean matchesWifi(String n,String verb){
        return n.matches("^(?:lutfen )?(?:wifi|wi fi|wi fi yi|wifiyi|wifi yi|kablosuz agi|kablosuz ag) "
                +verb+"(?:ar misin|er misin|abilir misin|abilir misiniz|iver|iver misin)?$")
            || n.matches("^(?:lutfen )?"+verb+" (?:wifi|wi fi|wifiyi|kablosuz agi|kablosuz ag)$");
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
