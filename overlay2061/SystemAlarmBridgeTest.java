package com.hakan.jarvis;

import java.util.Calendar;
import java.util.TimeZone;

public final class SystemAlarmBridgeTest {
    private static int pass=0,fail=0;

    private static long base(){
        Calendar c=Calendar.getInstance(TimeZone.getDefault());
        c.set(Calendar.YEAR,2026);c.set(Calendar.MONTH,Calendar.SEPTEMBER);c.set(Calendar.DAY_OF_MONTH,29);
        c.set(Calendar.HOUR_OF_DAY,15);c.set(Calendar.MINUTE,30);c.set(Calendar.SECOND,0);c.set(Calendar.MILLISECOND,0);
        return c.getTimeInMillis();
    }

    private static void expect(String raw,int hour,int minute){
        SystemAlarmBridge.Plan p=SystemAlarmBridge.parse(raw,base());
        if(p!=null&&p.hour==hour&&p.minute==minute)pass++;
        else{fail++;System.out.println("FAIL "+raw+" -> "+(p==null?"null":p.timeText()));}
    }

    private static void none(String raw){
        if(SystemAlarmBridge.parse(raw,base())==null)pass++;
        else{fail++;System.out.println("FAIL expected null "+raw);}
    }

    public static void main(String[] args){
        expect("20 dakika sonra alarm kur",15,50);
        expect("yarım saat sonra beni uyandır",16,0);
        expect("2 saat sonra alarm kur",17,30);
        expect("saat 7 ye alarm kur",7,0);
        expect("07:30 alarm kur",7,30);
        expect("alarm 8:45",8,45);
        expect("akşam 8 e alarm kur",20,0);
        expect("öğleden sonra saat 3 alarm kur",15,0);
        none("alarmı kapat");
        none("yarın hava nasıl");
        none("bluetooth aç");
        System.out.println("SystemAlarmBridge: PASS "+pass+" / FAIL "+fail);
        if(fail>0)System.exit(1);
    }
}
