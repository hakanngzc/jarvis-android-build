package com.newstargames.newstarsoccer;

import android.opengl.GLSurfaceView;
import android.os.Bundle;
import android.view.View;
import android.view.ViewGroup;

/**
 * Minimal lifecycle compatibility shim for NSS 4.31.
 *
 * The stock MonkeyGame/AndroidGame lifecycle remains authoritative.  This
 * subclass only enables Android's EGL-context preservation flag on the
 * existing GLSurfaceView before the stock focus-loss/focus-gain callbacks
 * invoke GLSurfaceView.onPause()/onResume().
 */
public final class RebornGame extends MonkeyGame {
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
