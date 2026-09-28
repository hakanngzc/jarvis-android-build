package com.hakan.jarvis;

import android.app.Activity;
import android.app.Application;
import android.os.Bundle;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.view.ViewGroup;
import java.io.InputStream;
import java.util.WeakHashMap;

public final class JarvisApplication extends Application implements Application.ActivityLifecycleCallbacks {
    private final WeakHashMap<Activity, Drawable> injected = new WeakHashMap<Activity, Drawable>();

    @Override public void onCreate() {
        super.onCreate();
        registerActivityLifecycleCallbacks(this);
    }

    private int dp(Activity a, int value) {
        return (int)(value * a.getResources().getDisplayMetrics().density + 0.5f);
    }

    private void inject(Activity a) {
        if (a == null || !"com.hakan.jarvis.HybridActivity".equals(a.getClass().getName())) return;
        if (injected.containsKey(a)) return;
        try {
            ViewGroup content = (ViewGroup)a.findViewById(android.R.id.content);
            if (content == null) return;
            InputStream in = a.getAssets().open("jarvis_core.webp");
            Bitmap bmp = BitmapFactory.decodeStream(in);
            in.close();
            if (bmp == null) return;
            BitmapDrawable d = new BitmapDrawable(a.getResources(), bmp);
            int size = dp(a, 250);
            int width = content.getWidth();
            if (width <= 0) width = a.getResources().getDisplayMetrics().widthPixels;
            int left = Math.max(0, (width - size) / 2);
            int top = dp(a, 145);
            d.setBounds(left, top, left + size, top + size);
            content.getOverlay().add(d);
            injected.put(a, d);
        } catch (Throwable ignored) {}
    }

    @Override public void onActivityCreated(Activity a, Bundle b) {
        final Activity activity = a;
        a.getWindow().getDecorView().post(new Runnable() {
            @Override public void run() { inject(activity); }
        });
    }
    @Override public void onActivityResumed(Activity a) { inject(a); }
    @Override public void onActivityDestroyed(Activity a) {
        Drawable d = injected.remove(a);
        if (d != null) {
            try {
                ViewGroup content=(ViewGroup)a.findViewById(android.R.id.content);
                if(content!=null) content.getOverlay().remove(d);
            } catch(Throwable ignored) {}
        }
    }
    @Override public void onActivityStarted(Activity a) {}
    @Override public void onActivityPaused(Activity a) {}
    @Override public void onActivityStopped(Activity a) {}
    @Override public void onActivitySaveInstanceState(Activity a, Bundle b) {}
}
