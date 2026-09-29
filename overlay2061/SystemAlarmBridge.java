package com.hakan.jarvis;

import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.provider.AlarmClock;
import java.util.Calendar;
import java.util.Locale;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public final class SystemAlarmBridge {
    public static final String PROFILE="SYSTEM_CLOCK_ALARM_V1";

    public static final class Plan {
        public final int hour;
        public final int minute;
        public final boolean relative;
        public final int relativeMinutes;
        public final String label;
        public final String source;

        Plan(int hour,int minute,boolean relative,int relativeMinutes,String label,String source){
            this.hour=hour;
            this.minute=minute;
            this.relative=relative;
            this.relativeMinutes=relativeMinutes;
            this.label=label==null?"JARVIS":label;
            this.source=source==null?"":source;
        }

        public String timeText(){
            return String.format(new Locale("tr","TR"),"%02d:%02d",hour,minute);
        }
    }

    public static final class Result {
        public final boolean success;
        public final String note;
        Result(boolean success,String note){
            this.success=success;
            this.note=note==null?"":note;
        }
    }

    private SystemAlarmBridge(){}

    public static Plan parse(String raw,long nowMillis){
        if(raw==null)return null;
        String q=normalize(raw);
        if(q.length()==0)return null;

        boolean alarmIntent=containsAny(q,"alarm","uyandir");
        if(!alarmIntent)return null;
        if(containsAny(q,"alarm kapat","alarmi kapat","alarm sil","alarmi sil","alarm iptal","alarmi iptal"))
            return null;

        int relative=-1;
        if(q.contains("yarim saat sonra"))relative=30;

        Matcher m=Pattern.compile("(\\d{1,4})\\s*(?:dakika|dk)\\s*sonra").matcher(q);
        if(m.find())relative=safeInt(m.group(1),-1);

        Matcher h=Pattern.compile("(\\d{1,2})\\s*saat\\s*sonra").matcher(q);
        if(h.find()){
            int hours=safeInt(h.group(1),-1);
            if(hours>=1&&hours<=24)relative=hours*60;
        }

        if(relative>=1&&relative<=1440){
            Calendar c=Calendar.getInstance();
            c.setTimeInMillis(nowMillis);
            c.add(Calendar.MINUTE,relative);
            return new Plan(c.get(Calendar.HOUR_OF_DAY),c.get(Calendar.MINUTE),true,relative,"JARVIS",q);
        }

        int[] hm=parseAbsolute(q);
        if(hm==null)return null;
        return new Plan(hm[0],hm[1],false,-1,"JARVIS",q);
    }

    private static int[] parseAbsolute(String q){
        Matcher colon=Pattern.compile("(?:saat\\s*)?(\\d{1,2})\\s*[:.]\\s*([0-5]\\d)").matcher(q);
        if(colon.find()){
            int hour=safeInt(colon.group(1),-1);
            int min=safeInt(colon.group(2),-1);
            hour=applyDayPart(hour,q);
            if(valid(hour,min))return new int[]{hour,min};
        }

        Matcher hourOnly=Pattern.compile("(?:saat\\s*)?(\\d{1,2})\\s*(?:ye|ya|e|a)?\\s*(?:icin\\s*)?(?:alarm|alarma)").matcher(q);
        if(hourOnly.find()){
            int hour=applyDayPart(safeInt(hourOnly.group(1),-1),q);
            if(valid(hour,0))return new int[]{hour,0};
        }

        Matcher alarmFirst=Pattern.compile("(?:alarm|alarmi)\\s*(?:saat\\s*)?(\\d{1,2})(?:\\s*[:.]\\s*([0-5]\\d))?").matcher(q);
        if(alarmFirst.find()){
            int hour=applyDayPart(safeInt(alarmFirst.group(1),-1),q);
            int min=alarmFirst.group(2)==null?0:safeInt(alarmFirst.group(2),-1);
            if(valid(hour,min))return new int[]{hour,min};
        }

        Matcher clockPhrase=Pattern.compile("saat\\s*(\\d{1,2})(?:\\s*[:.]\\s*([0-5]\\d))?").matcher(q);
        if(clockPhrase.find()){
            int hour=applyDayPart(safeInt(clockPhrase.group(1),-1),q);
            int min=clockPhrase.group(2)==null?0:safeInt(clockPhrase.group(2),-1);
            if(valid(hour,min))return new int[]{hour,min};
        }

        return null;
    }

    private static int applyDayPart(int hour,String q){
        if(hour<0||hour>23)return hour;
        if(containsAny(q,"aksam","ogleden sonra")&&hour>=1&&hour<=11)return hour+12;
        if(q.contains("ogle")&&hour>=1&&hour<=11)return hour==12?12:hour+12;
        return hour;
    }

    private static boolean valid(int h,int m){return h>=0&&h<=23&&m>=0&&m<=59;}

    public static Result setAlarm(Context context,Plan plan){
        if(context==null||plan==null)return new Result(false,"missing_context_or_plan");
        Intent i=new Intent(AlarmClock.ACTION_SET_ALARM);
        i.putExtra(AlarmClock.EXTRA_HOUR,plan.hour);
        i.putExtra(AlarmClock.EXTRA_MINUTES,plan.minute);
        i.putExtra(AlarmClock.EXTRA_MESSAGE,plan.label);
        i.putExtra(AlarmClock.EXTRA_SKIP_UI,true);
        if(android.os.Build.VERSION.SDK_INT>=19){
            i.putExtra(AlarmClock.EXTRA_VIBRATE,true);
        }
        if(!(context instanceof android.app.Activity))i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try{
            context.startActivity(i);
            return new Result(true,"system_clock_intent_started");
        }catch(ActivityNotFoundException e){
            return new Result(false,"no_alarm_clock_handler");
        }catch(SecurityException e){
            return new Result(false,"set_alarm_permission_rejected");
        }catch(Exception e){
            return new Result(false,e.getClass().getSimpleName());
        }
    }

    public static Result showAlarms(Context context){
        if(context==null)return new Result(false,"missing_context");
        Intent i=new Intent(AlarmClock.ACTION_SHOW_ALARMS);
        if(!(context instanceof android.app.Activity))i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try{
            context.startActivity(i);
            return new Result(true,"system_alarm_list_opened");
        }catch(Exception e){
            return new Result(false,e.getClass().getSimpleName());
        }
    }

    static String normalize(String raw){
        String s=raw.toLowerCase(new Locale("tr","TR"))
            .replace('ı','i').replace('ğ','g').replace('ü','u')
            .replace('ş','s').replace('ö','o').replace('ç','c')
            .replace('’',' ').replace('\'',' ');
        s=s.replaceAll("[^a-z0-9:. ]+"," ");
        return s.replaceAll("\\s+"," ").trim();
    }

    private static boolean containsAny(String s,String... xs){
        for(String x:xs)if(s.contains(x))return true;
        return false;
    }

    private static int safeInt(String s,int d){
        try{return Integer.parseInt(s);}catch(Exception e){return d;}
    }
}
