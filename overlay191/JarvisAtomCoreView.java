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
    private static final String RENDER_PROFILE = "ULTRA_ATOM_V2";

    private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint brightRing = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint electron = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint particle = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint glow = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint arc = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF oval = new RectF();

    private final float[] particlePhase = new float[]{
        12f,38f,67f,94f,123f,151f,178f,206f,232f,259f,286f,314f,
        21f,54f,89f,137f,169f,198f,241f,276f,308f,341f,112f,224f
    };
    private final float[] particleRadius = new float[]{
        .25f,.29f,.33f,.37f,.27f,.35f,.31f,.39f,.28f,.36f,.32f,.40f,
        .26f,.34f,.30f,.38f,.24f,.41f,.285f,.365f,.315f,.395f,.345f,.255f
    };
    private final float[] particleSpeed = new float[]{
        1f,-.72f,1.35f,-1.15f,.84f,-1.42f,1.12f,-.93f,1.5f,-.66f,1.22f,-1.28f,
        .76f,-1.36f,1.06f,-.88f,1.44f,-1.02f,.69f,-1.18f,1.31f,-.81f,1.53f,-1.47f
    };

    private float angle = 0f;
    private float pulse = 0f;
    private int mode = 0; // 0 idle, 1 listening, 2 responding
    private ValueAnimator animator;

    public JarvisAtomCoreView(Context context) {
        super(context);
        setLayerType(View.LAYER_TYPE_HARDWARE, null);

        ring.setStyle(Paint.Style.STROKE);
        ring.setStrokeCap(Paint.Cap.ROUND);
        brightRing.setStyle(Paint.Style.STROKE);
        brightRing.setStrokeCap(Paint.Cap.ROUND);
        arc.setStyle(Paint.Style.STROKE);
        arc.setStrokeCap(Paint.Cap.ROUND);

        electron.setStyle(Paint.Style.FILL);
        particle.setStyle(Paint.Style.FILL);

        startAnimation();
    }

    private float dp(float v) {
        return v * getResources().getDisplayMetrics().density;
    }

    public void setMode(int value) {
        mode = value;
        invalidate();
    }

    private float speed() {
        if (mode == 1) return 1.72f;
        if (mode == 2) return 1.33f;
        return 1f;
    }

    private void startAnimation() {
        if (animator != null) animator.cancel();
        animator = ValueAnimator.ofFloat(0f, 360f);
        animator.setDuration(7600L);
        animator.setRepeatCount(ValueAnimator.INFINITE);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(a -> {
            angle = (Float)a.getAnimatedValue();
            pulse = (float)((Math.sin(Math.toRadians(angle * 2.35)) + 1.0) * 0.5);
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
        if (w <= 0 || h <= 0) return;

        float cx = w * 0.5f, cy = h * 0.5f;
        float min = Math.min(w, h);
        float s = speed();
        float a = angle * s;
        float base = min * 0.345f;

        drawEnergyField(c, cx, cy, min, a);
        drawConcentricCore(c, cx, cy, min, a);

        drawOrbitLayer(c, cx, cy, base,       base*.40f,  a,          0f, 0);
        drawOrbitLayer(c, cx, cy, base*.97f,  base*.42f, -a*.82f,    58f, 1);
        drawOrbitLayer(c, cx, cy, base*.94f,  base*.38f,  a*1.17f,  -58f, 2);
        drawOrbitLayer(c, cx, cy, base*.86f,  base*.31f, -a*1.38f,   28f, 3);
        drawOrbitLayer(c, cx, cy, base*.80f,  base*.28f,  a*1.62f,  -31f, 4);
        drawOrbitLayer(c, cx, cy, base*.72f,  base*.23f, -a*1.91f,   83f, 5);
        drawOrbitLayer(c, cx, cy, base*.66f,  base*.20f,  a*2.18f,  -82f, 6);

        drawParticleCloud(c, cx, cy, min, a);
        drawCoreNucleus(c, cx, cy, min, a);
    }

    private void drawEnergyField(Canvas c,float cx,float cy,float min,float a) {
        float glowRadius = min * (.205f + .030f*pulse + (mode==1?.018f:0f));
        int center = mode==1 ? 0xdd82efff : (mode==2 ? 0xcc67ddff : 0xaa5de8ff);
        glow.setShader(new RadialGradient(
            cx,cy,glowRadius,
            new int[]{center,0x663cbcff,0x223086d8,0x00000b14},
            new float[]{0f,.30f,.62f,1f},
            Shader.TileMode.CLAMP
        ));
        c.drawCircle(cx,cy,glowRadius,glow);

        glow.setShader(null);
        ring.setStyle(Paint.Style.STROKE);
        ring.setStrokeWidth(dp(mode==1?1.6f:1.0f));
        ring.setColor(mode==1?0x5538bfff:0x3338aeea);

        for(int i=0;i<5;i++){
            float r=min*(.235f+i*.039f)+pulse*dp(1.2f+i*.15f);
            c.drawCircle(cx,cy,r,ring);
        }

        arc.setStrokeWidth(dp(mode==1?2.2f:1.35f));
        arc.setColor(mode==1?0xaa54d7ff:0x6654c4ff);
        for(int i=0;i<4;i++){
            float r=min*(.255f+i*.050f);
            oval.set(cx-r,cy-r,cx+r,cy+r);
            float start=(a*(i%2==0?1f:-.72f)+i*87f)%360f;
            c.drawArc(oval,start,34f+i*8f,false,arc);
            c.drawArc(oval,start+178f,18f+i*5f,false,arc);
        }
    }

    private void drawConcentricCore(Canvas c,float cx,float cy,float min,float a) {
        brightRing.setStrokeWidth(dp(mode==1?2.0f:1.25f));
        for(int i=0;i<4;i++){
            int alpha=150-i*25;
            brightRing.setColor((alpha<<24)|0x0039bfff);
            float r=min*(.095f+i*.031f)+pulse*dp(.8f+i*.25f);
            c.drawCircle(cx,cy,r,brightRing);
        }

        arc.setStrokeWidth(dp(2.0f));
        arc.setColor(mode==1?0xddbaf5ff:0x99a1eaff);
        float r=min*.145f;
        oval.set(cx-r,cy-r,cx+r,cy+r);
        c.drawArc(oval,a*2.4f,82f,false,arc);
        c.drawArc(oval,-a*1.9f+145f,46f,false,arc);
    }

    private void drawOrbitLayer(Canvas c,float cx,float cy,float rx,float ry,float rotation,float tilt,int index) {
        int alpha;
        if(mode==1) alpha=205-index*12;
        else if(mode==2) alpha=180-index*13;
        else alpha=135-index*11;
        if(alpha<45)alpha=45;

        ring.setColor((alpha<<24)|0x0039bfff);
        ring.setStrokeWidth(dp(index<3?(mode==1?1.8f:1.25f):.9f));

        c.save();
        c.rotate(tilt,cx,cy);
        oval.set(cx-rx,cy-ry,cx+rx,cy+ry);
        c.drawOval(oval,ring);

        arc.setStrokeWidth(dp(index<3?2.4f:1.5f));
        arc.setColor(((Math.min(235,alpha+40))<<24)|0x005de2ff);
        float sweep=index%2==0?42f:28f;
        c.drawArc(oval,rotation*.65f+index*43f,sweep,false,arc);
        c.restore();

        int count=index<3?3:2;
        for(int i=0;i<count;i++){
            float phase=rotation+i*(360f/count)+index*31f;
            drawOrbitElectron(c,cx,cy,rx,ry,phase,tilt,index,i);
        }
    }

    private void drawOrbitElectron(Canvas c,float cx,float cy,float rx,float ry,float deg,float tilt,int orbit,int electronIndex) {
        float[] pos=orbitPoint(cx,cy,rx,ry,deg,tilt);
        float size=dp((mode==1?4.5f:3.4f) - orbit*.16f);
        if(size<dp(2.2f))size=dp(2.2f);

        particle.setColor(mode==1?0x445ce6ff:0x2250caff);
        c.drawCircle(pos[0],pos[1],size*2.7f,particle);

        electron.setColor(electronIndex%2==0?0xffeffdff:0xff7de9ff);
        c.drawCircle(pos[0],pos[1],size,electron);

        // trailing sparks
        for(int t=1;t<=3;t++){
            float back=deg-(t*(mode==1?5.8f:4.1f));
            float[] tail=orbitPoint(cx,cy,rx,ry,back,tilt);
            int al=95-t*22;
            particle.setColor((al<<24)|0x005de4ff);
            c.drawCircle(tail[0],tail[1],Math.max(dp(.9f),size*(.55f-t*.10f)),particle);
        }
    }

    private float[] orbitPoint(float cx,float cy,float rx,float ry,float deg,float tilt) {
        double t=Math.toRadians(deg);
        float x=(float)(Math.cos(t)*rx);
        float y=(float)(Math.sin(t)*ry);
        double r=Math.toRadians(tilt);
        float xr=(float)(x*Math.cos(r)-y*Math.sin(r));
        float yr=(float)(x*Math.sin(r)+y*Math.cos(r));
        return new float[]{cx+xr,cy+yr};
    }

    private void drawParticleCloud(Canvas c,float cx,float cy,float min,float a) {
        for(int i=0;i<particlePhase.length;i++){
            float deg=particlePhase[i]+a*particleSpeed[i];
            float radius=min*particleRadius[i];
            double t=Math.toRadians(deg);
            float wobble=(float)Math.sin(Math.toRadians(a*1.7f+i*23f))*min*.012f;
            float x=cx+(float)Math.cos(t)*(radius+wobble);
            float y=cy+(float)Math.sin(t)*(radius*.72f-wobble*.35f);
            float twinkle=.5f+.5f*(float)Math.sin(Math.toRadians(a*2.1f+i*41f));
            int al=(int)((mode==1?115:75)+twinkle*(mode==1?120:90));
            if(al>245)al=245;
            float size=dp(.8f+twinkle*(mode==1?2.0f:1.25f));
            particle.setColor((al<<24)|0x005be2ff);
            c.drawCircle(x,y,size,particle);
        }
    }

    private void drawCoreNucleus(Canvas c,float cx,float cy,float min,float a) {
        particle.setColor(mode==1?0x665eeaff:0x335eeaff);
        c.drawCircle(cx,cy,min*(.050f+.010f*pulse),particle);

        electron.setColor(0xfff5feff);
        c.drawCircle(cx,cy,dp(4.8f+2.2f*pulse+(mode==1?2.0f:0f)),electron);

        brightRing.setStrokeWidth(dp(mode==1?2.2f:1.4f));
        brightRing.setColor(mode==1?0xee9af2ff:0xaa72dfff);
        float r=min*(.063f+.006f*pulse);
        c.drawCircle(cx,cy,r,brightRing);

        // four fast inner electrons
        for(int i=0;i<4;i++){
            float deg=a*2.6f+i*90f;
            float rr=min*.078f;
            float x=cx+(float)Math.cos(Math.toRadians(deg))*rr;
            float y=cy+(float)Math.sin(Math.toRadians(deg))*rr*.58f;
            electron.setColor(i%2==0?0xffffffff:0xff79eaff);
            c.drawCircle(x,y,dp(mode==1?2.8f:2.0f),electron);
        }
    }
}
