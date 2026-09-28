package com.hakan.jarvis;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.RectF;
import android.graphics.Shader;
import android.view.View;
import android.view.animation.LinearInterpolator;

public final class JarvisAtomCoreView extends View {
    private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint electron = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint glow = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF oval = new RectF();
    private float angle = 0f;
    private float pulse = 0f;
    private int mode = 0; // 0 idle, 1 listening, 2 responding
    private ValueAnimator animator;

    public JarvisAtomCoreView(Context context) {
        super(context);
        setLayerType(View.LAYER_TYPE_HARDWARE, null);
        ring.setStyle(Paint.Style.STROKE);
        ring.setStrokeWidth(dp(1.2f));
        ring.setColor(0x8839bfff);
        electron.setStyle(Paint.Style.FILL);
        electron.setColor(0xffdff8ff);
        startAnimation();
    }

    private float dp(float v) {
        return v * getResources().getDisplayMetrics().density;
    }

    public void setMode(int value) {
        mode = value;
        invalidate();
    }

    private void startAnimation() {
        animator = ValueAnimator.ofFloat(0f, 360f);
        animator.setDuration(7000L);
        animator.setRepeatCount(ValueAnimator.INFINITE);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(a -> {
            angle = (Float)a.getAnimatedValue();
            pulse = (float)((Math.sin(Math.toRadians(angle * 2.0)) + 1.0) * 0.5);
            invalidate();
        });
        animator.start();
    }

    @Override protected void onDetachedFromWindow() {
        super.onDetachedFromWindow();
        if (animator != null) animator.cancel();
    }

    @Override protected void onAttachedToWindow() {
        super.onAttachedToWindow();
        if (animator == null || !animator.isRunning()) startAnimation();
    }

    @Override protected void onDraw(Canvas c) {
        super.onDraw(c);
        float w = getWidth(), h = getHeight();
        float cx = w * 0.5f, cy = h * 0.5f;
        float min = Math.min(w, h);
        float base = min * 0.34f;

        int alpha = mode == 1 ? 210 : (mode == 2 ? 185 : 125);
        ring.setColor((alpha << 24) | 0x0039bfff);
        ring.setStrokeWidth(dp(mode == 1 ? 1.8f : 1.2f));

        glow.setShader(new RadialGradient(
            cx, cy,
            min * (0.19f + 0.025f * pulse),
            new int[]{0x995de8ff, 0x443aaeff, 0x00001222},
            new float[]{0f, 0.45f, 1f},
            Shader.TileMode.CLAMP
        ));
        c.drawCircle(cx, cy, min * (0.19f + 0.025f * pulse), glow);

        drawOrbit(c, cx, cy, base, base * 0.42f, angle, 0);
        drawOrbit(c, cx, cy, base, base * 0.42f, -angle * 0.82f, 60);
        drawOrbit(c, cx, cy, base, base * 0.42f, angle * 1.18f, -60);

        ring.setColor(0x5539bfff);
        for (int i=0;i<3;i++) {
            c.drawCircle(cx, cy, min * (0.245f + i*0.055f) + pulse*dp(1.5f), ring);
        }

        electron.setColor(mode == 1 ? 0xffffffff : 0xffc8f4ff);
        drawElectron(c, cx, cy, base, base * 0.42f, angle, 0);
        drawElectron(c, cx, cy, base, base * 0.42f, -angle * 0.82f + 125f, 60);
        drawElectron(c, cx, cy, base, base * 0.42f, angle * 1.18f + 245f, -60);

        electron.setColor(0xfff4fdff);
        c.drawCircle(cx, cy, dp(4f + 2f*pulse + (mode==1?2f:0f)), electron);
    }

    private void drawOrbit(Canvas c,float cx,float cy,float rx,float ry,float rotation,float tilt) {
        c.save();
        c.rotate(tilt, cx, cy);
        oval.set(cx-rx, cy-ry, cx+rx, cy+ry);
        c.drawOval(oval, ring);
        c.restore();
    }

    private void drawElectron(Canvas c,float cx,float cy,float rx,float ry,float deg,float tilt) {
        double t = Math.toRadians(deg);
        float x = (float)(Math.cos(t)*rx);
        float y = (float)(Math.sin(t)*ry);
        double r = Math.toRadians(tilt);
        float xr = (float)(x*Math.cos(r)-y*Math.sin(r));
        float yr = (float)(x*Math.sin(r)+y*Math.cos(r));
        c.drawCircle(cx+xr, cy+yr, dp(mode==1?4.2f:3.2f), electron);
    }
}
