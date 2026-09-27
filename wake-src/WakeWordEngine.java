package com.hakan.jarvis;
import android.content.*;
public final class WakeWordEngine {
    private final SharedPreferences p;
    public WakeWordEngine(Context c){p=c.getSharedPreferences("jarvis_wake",Context.MODE_PRIVATE);}
    public boolean trained(){return p.getBoolean("enabled",false);}
    public void clear(){p.edit().putBoolean("enabled",true).apply();}
    public void enable(){p.edit().putBoolean("enabled",true).apply();}
    public void disable(){p.edit().putBoolean("enabled",false).apply();}
}