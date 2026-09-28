package com.hakan.jarvis;

import android.app.Activity;
import android.bluetooth.BluetoothAdapter;
import android.content.Context;
import android.content.Intent;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.provider.Settings;

public final class DeviceActions {
    public static final String PROFILE="DEVICE_ACTIONS_V1";

    public static final class Result {
        public final boolean direct;
        public final boolean panelOpened;
        public final boolean alreadyInState;
        public final String note;

        Result(boolean direct,boolean panelOpened,boolean alreadyInState,String note){
            this.direct=direct;
            this.panelOpened=panelOpened;
            this.alreadyInState=alreadyInState;
            this.note=note==null?"":note;
        }

        static Result direct(boolean already,String note){
            return new Result(true,false,already,note);
        }

        static Result panel(String note){
            return new Result(false,true,false,note);
        }
    }

    private DeviceActions(){}

    public static Result execute(Activity a,DeviceCommandRouter.Command c){
        if(c==null)throw new IllegalArgumentException("command");
        if("BLUETOOTH_ON".equals(c.action))return bluetooth(a,true);
        if("BLUETOOTH_OFF".equals(c.action))return bluetooth(a,false);
        if("WIFI_ON".equals(c.action))return wifi(a,true);
        if("WIFI_OFF".equals(c.action))return wifi(a,false);
        throw new IllegalArgumentException("Unsupported device action");
    }

    static Result bluetooth(Activity a,boolean enable){
        BluetoothAdapter adapter=BluetoothAdapter.getDefaultAdapter();
        if(adapter==null)return openBluetoothSettings(a,"Bluetooth donanımı bulunamadı.");

        try{
            boolean on=adapter.isEnabled();
            if(on==enable)return Result.direct(true,enable?"Bluetooth zaten açık.":"Bluetooth zaten kapalı.");

            boolean accepted;
            if(enable)accepted=adapter.enable();
            else accepted=adapter.disable();

            if(accepted)return Result.direct(false,enable?"Bluetooth açma isteği gönderildi.":"Bluetooth kapatma isteği gönderildi.");
        }catch(SecurityException ignored){}
        catch(Exception ignored){}

        if(enable){
            try{
                Intent i=new Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE);
                a.startActivity(i);
                return Result.panel("Android Bluetooth açma onayı istedi.");
            }catch(Exception ignored){}
        }

        return openBluetoothSettings(a,"Android Bluetooth'u doğrudan değiştirmeye izin vermedi.");
    }

    static Result wifi(Activity a,boolean enable){
        try{
            WifiManager wifi=(WifiManager)a.getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if(wifi!=null){
                boolean on=wifi.isWifiEnabled();
                if(on==enable)return Result.direct(true,enable?"Wi-Fi zaten açık.":"Wi-Fi zaten kapalı.");
                boolean accepted=wifi.setWifiEnabled(enable);
                if(accepted)return Result.direct(false,enable?"Wi-Fi açma isteği gönderildi.":"Wi-Fi kapatma isteği gönderildi.");
            }
        }catch(SecurityException ignored){}
        catch(Exception ignored){}

        return openWifiPanel(a,"Android Wi-Fi'yi doğrudan değiştirmeye izin vermedi.");
    }

    static Result openBluetoothSettings(Activity a,String note){
        try{
            a.startActivity(new Intent(Settings.ACTION_BLUETOOTH_SETTINGS));
            return Result.panel(note);
        }catch(Exception e){
            a.startActivity(new Intent(Settings.ACTION_SETTINGS));
            return Result.panel(note);
        }
    }

    static Result openWifiPanel(Activity a,String note){
        try{
            if(Build.VERSION.SDK_INT>=29){
                a.startActivity(new Intent(Settings.Panel.ACTION_WIFI));
            }else{
                a.startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
            }
            return Result.panel(note);
        }catch(Exception e){
            a.startActivity(new Intent(Settings.ACTION_WIFI_SETTINGS));
            return Result.panel(note);
        }
    }

    public static String fallbackVoice(DeviceCommandRouter.Command c){
        if(c==null)return "Android doğrudan değiştirmeye izin vermedi efendim. Ayar ekranını açtım.";
        if(c.action.startsWith("BLUETOOTH"))
            return "Android Bluetooth'u doğrudan değiştirmeye izin vermedi efendim. Bluetooth ayarlarını açtım.";
        if(c.action.startsWith("WIFI"))
            return "Android Wi-Fi'yi doğrudan değiştirmeye izin vermedi efendim. Wi-Fi kontrolünü açtım.";
        return "Android doğrudan değiştirmeye izin vermedi efendim. Ayar ekranını açtım.";
    }
}
