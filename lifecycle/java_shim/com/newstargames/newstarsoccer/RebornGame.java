package com.newstargames.newstarsoccer;

import android.content.SharedPreferences;
import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;

/**
 * Minimal lifecycle compatibility shim for NSS 4.31.
 *
 * The stock MonkeyGame/AndroidGame lifecycle remains authoritative. This
 * subclass only enables Android's EGL-context preservation flag on the
 * existing GLSurfaceView before stock focus-loss/focus-gain callbacks invoke
 * GLSurfaceView.onPause()/onResume().
 *
 * NSS persists through Activity.getPreferences(0), whose default namespace is
 * derived from the Activity class name. Because this shim changes the launcher
 * Activity name, explicitly retain the stock MonkeyGame preference namespace
 * so existing careers continue to use MonkeyGame.xml.
 */
public final class RebornGame extends MonkeyGame {
    @Override
    public SharedPreferences getPreferences(int mode) {
        return getSharedPreferences("MonkeyGame", mode);
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        preserveEglContext(getWindow().getDecorView());
    }

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {
        if (hasFocus) {
            preserveEglContext(getWindow().getDecorView());
        }
        super.onWindowFocusChanged(hasFocus);
    }

    private static void preserveEglContext(View view) {
        if (view instanceof GLSurfaceView) {
            ((GLSurfaceView) view).setPreserveEGLContextOnPause(true);
        }
        if (view instanceof ViewGroup) {
            ViewGroup group = (ViewGroup) view;
            for (int i = 0; i < group.getChildCount(); i++) {
                preserveEglContext(group.getChildAt(i));
            }
        }
    }
}
