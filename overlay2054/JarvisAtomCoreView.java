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
    public static final String RENDER_PROFILE = "ELITE_ATOM_V5_HYPER_MOTION";

    private final Paint orbit = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint frontOrbit = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint electron = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint glow = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint spark = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint arc = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final RectF oval = new RectF();

    private float phase=0f;
    private float pulse=0f;
    private int mode=0;
    private ValueAnimator animator;

    private final float[] cloudA={
        8,19,29,41,51,63,74,86,98,111,124,136,149,162,176,189,203,216,
        229,242,254,267,278,291,304,316,329,339,348,57,143,233,318,102,271,12
    };
    private final float[] cloudR={
        .29f,.345f,.34f,.405f,.38f,.315f,.32f,.42f,.41f,.30f,.36f,.395f,.30f,.43f,.39f,.325f,
        .33f,.415f,.42f,.305f,.31f,.37f,.37f,.285f,.28f,.40f,.40f,.35f,.35f,.43f,.27f,.365f,.325f,.395f,.355f,.31f
    };
    private final float[] cloudS={
        .54f,-.66f,-.71f,.82f,.91f,-.58f,-.62f,.88f,.77f,-.79f,-.83f,.64f,.67f,-.93f,-.95f,.73f,
        .58f,-.86f,-.74f,.96f,.88f,-.69f,.81f,-.90f,-.57f,.93f,-.79f,.63f,-.87f,.72f,-.66f,.84f,-.76f,.61f,-.94f,.69f
    };

    public JarvisAtomCoreView(Context c){
        super(c);
        setLayerType(View.LAYER_TYPE_HARDWARE,null);
        orbit.setStyle(Paint.Style.STROKE);
        orbit.setStrokeCap(Paint.Cap.ROUND);
        frontOrbit.setStyle(Paint.Style.STROKE);
        frontOrbit.setStrokeCap(Paint.Cap.ROUND);
        arc.setStyle(Paint.Style.STROKE);
        arc.setStrokeCap(Paint.Cap.ROUND);
        electron.setStyle(Paint.Style.FILL);
        spark.setStyle(Paint.Style.FILL);
        start();
    }

    private float dp(float v){return v*getResources().getDisplayMetrics().density;}

    public void setMode(int m){mode=m;invalidate();}

    private float speed(){
        if(mode==1)return 1.48f;
        if(mode==2)return 1.20f;
        return .82f;
    }

    private void start(){
        if(animator!=null)animator.cancel();
        animator=ValueAnimator.ofFloat(0f,360f);
        animator.setDuration(4500L);
        animator.setRepeatCount(ValueAnimator.INFINITE);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(a->{
            phase=(Float)a.getAnimatedValue();
            pulse=.5f+.5f*(float)Math.sin(Math.toRadians(phase*2.0f));
            invalidate();
        });
        animator.start();
    }

    @Override protected void onDetachedFromWindow(){super.onDetachedFromWindow();if(animator!=null)animator.cancel();}
    @Override protected void onAttachedToWindow(){super.onAttachedToWindow();if(animator==null||!animator.isRunning())start();}

    @Override protected void onDraw(Canvas c){
        super.onDraw(c);
        float w=getWidth(),h=getHeight();
        if(w<=0||h<=0)return;
        float cx=w*.5f,cy=h*.5f,min=Math.min(w,h);
        float a=phase*speed();

        drawAura(c,cx,cy,min,a);
        drawPulseShells(c,cx,cy,min,a);
        drawKineticRings(c,cx,cy,min,a);
        drawScanner(c,cx,cy,min,a);
        drawCore(c,cx,cy,min,a);

        float r=min*.365f;
        drawOrbit(c,cx,cy,r,       r*.36f,a,         0,0);
        drawOrbit(c,cx,cy,r*.97f,  r*.39f,-a*.84f,  56,1);
        drawOrbit(c,cx,cy,r*.93f,  r*.34f,a*1.08f, -56,2);
        drawOrbit(c,cx,cy,r*.88f,  r*.30f,-a*1.26f, 28,3);
        drawOrbit(c,cx,cy,r*.82f,  r*.26f,a*1.42f, -30,4);
        drawOrbit(c,cx,cy,r*.75f,  r*.23f,-a*1.58f, 82,5);
        drawOrbit(c,cx,cy,r*.68f,  r*.20f,a*1.76f, -78,6);
        drawOrbit(c,cx,cy,r*.60f,  r*.18f,-a*1.92f, 42,7);
        drawOrbit(c,cx,cy,r*.53f,  r*.16f,a*2.08f, -18,8);
        drawOrbit(c,cx,cy,r*.46f,  r*.14f,-a*2.25f, 68,9);

        drawHaloNodes(c,cx,cy,min,a);
        drawCloud(c,cx,cy,min,a);
        drawNucleus(c,cx,cy,min,a);
    }

    private void drawAura(Canvas c,float cx,float cy,float min,float a){
        float rr=min*(.215f+.020f*pulse+(mode==1?.014f:0));
        int center=mode==1?0xeea8f8ff:(mode==2?0xda82e9ff:0xb96ae2ff);
        glow.setShader(new RadialGradient(cx,cy,rr,
            new int[]{center,0x7054d8ff,0x30358cc9,0x0000070d},
            new float[]{0f,.32f,.67f,1f},Shader.TileMode.CLAMP));
        c.drawCircle(cx,cy,rr,glow);
        glow.setShader(null);

        orbit.setStrokeWidth(dp(.9f));
        for(int i=0;i<6;i++){
            orbit.setColor(((52-i*6)<<24)|0x003baeff);
            float rad=min*(.225f+i*.042f)+pulse*dp(.75f+i*.16f);
            c.drawCircle(cx,cy,rad,orbit);
        }

        arc.setStrokeWidth(dp(mode==1?2.0f:1.35f));
        for(int i=0;i<5;i++){
            float rad=min*(.245f+i*.041f);
            oval.set(cx-rad,cy-rad,cx+rad,cy+rad);
            int al=mode==1?140:(92-i*7);
            arc.setColor((al<<24)|0x004bcaff);
            float spin=a*(i%2==0?.72f:-.58f)+i*71f;
            c.drawArc(oval,spin,21f+i*5f,false,arc);
            c.drawArc(oval,spin+128f,12f+i*3f,false,arc);
            c.drawArc(oval,spin+232f,18f+i*4f,false,arc);
        }
    }

    private void drawPulseShells(Canvas c,float cx,float cy,float min,float a){
        arc.setStrokeWidth(dp(1.05f));
        for(int i=0;i<3;i++){
            float local=(phase+i*120f)%360f;
            float t=local/360f;
            float rad=min*(.14f+.29f*t);
            int alpha=(int)(95*(1f-t));
            if(alpha<8)alpha=8;
            arc.setColor((alpha<<24)|0x0049d8ff);
            oval.set(cx-rad,cy-rad,cx+rad,cy+rad);
            c.drawArc(oval,a*.18f+i*88f,265f,false,arc);
        }
    }

    private void drawKineticRings(Canvas c,float cx,float cy,float min,float a){
        arc.setStrokeWidth(dp(1.15f));
        for(int ring=0;ring<4;ring++){
            float rad=min*(.115f+ring*.047f);
            oval.set(cx-rad,cy-rad,cx+rad,cy+rad);
            float spin=a*(ring%2==0?1.35f:-1.12f)+ring*53f;
            int alpha=150-ring*22;
            arc.setColor((alpha<<24)|0x006ce8ff);
            for(int seg=0;seg<4;seg++){
                c.drawArc(oval,spin+seg*90f,18f+ring*3f,false,arc);
            }
        }
    }

    private void drawScanner(Canvas c,float cx,float cy,float min,float a){
        orbit.setStrokeWidth(dp(.75f));
        for(int i=0;i<6;i++){
            float deg=a*.88f+i*60f;
            float rad1=min*.17f;
            float rad2=min*(.30f+.018f*(i%2));
            float cs=(float)Math.cos(Math.toRadians(deg));
            float sn=(float)Math.sin(Math.toRadians(deg));
            int alpha=34+i*5;
            orbit.setColor((alpha<<24)|0x0047cfff);
            c.drawLine(cx+cs*rad1,cy+sn*rad1,cx+cs*rad2,cy+sn*rad2,orbit);
        }
    }

    private void drawCore(Canvas c,float cx,float cy,float min,float a){
        orbit.setStrokeWidth(dp(1.15f));
        for(int i=0;i<5;i++){
            int al=145-i*20;
            orbit.setColor((al<<24)|0x0047cfff);
            c.drawCircle(cx,cy,min*(.068f+i*.026f)+pulse*dp(.38f+i*.08f),orbit);
        }
        arc.setStrokeWidth(dp(1.8f));
        arc.setColor(mode==1?0xe5c8fbff:0xa98ae7ff);
        float r=min*.153f; oval.set(cx-r,cy-r,cx+r,cy+r);
        c.drawArc(oval,a*1.35f,68,false,arc);
        c.drawArc(oval,-a*1.05f+158,34,false,arc);
        c.drawArc(oval,a*.74f+262,21,false,arc);
    }

    private void drawOrbit(Canvas c,float cx,float cy,float rx,float ry,float spin,float baseTilt,int idx){
        float precess=(float)Math.sin(Math.toRadians(phase*.27f+idx*47f))*8.5f;
        float tilt=baseTilt+precess;

        int backAlpha=mode==1?88:58;
        orbit.setColor((backAlpha<<24)|0x0038aeea);
        orbit.setStrokeWidth(dp(idx<3?1.12f:.78f));
        c.save();
        c.rotate(tilt,cx,cy);
        oval.set(cx-rx,cy-ry,cx+rx,cy+ry);
        c.drawOval(oval,orbit);

        int frontAlpha=mode==1?220:(mode==2?185:158);
        frontOrbit.setColor((frontAlpha<<24)|0x0052d9ff);
        frontOrbit.setStrokeWidth(dp(idx<3?1.82f:1.14f));
        float start=(spin*.35f+idx*31f)%360f;
        c.drawArc(oval,start,105,false,frontOrbit);
        c.drawArc(oval,start+146,37,false,frontOrbit);
        c.drawArc(oval,start+232,24,false,frontOrbit);
        c.restore();

        int count=idx<4?3:2;
        for(int e=0;e<count;e++){
            float deg=spin+e*(360f/count)+idx*29f;
            drawElectron(c,cx,cy,rx,ry,deg,tilt,idx,e);
        }
    }

    private void drawElectron(Canvas c,float cx,float cy,float rx,float ry,float deg,float tilt,int orbitIdx,int electronIdx){
        double t=Math.toRadians(deg);
        float depth=.5f+.5f*(float)Math.sin(t);
        double rot=Math.toRadians(tilt);
        float ex=(float)Math.cos(t)*rx;
        float ey=(float)Math.sin(t)*ry;
        float px=cx+(float)(ex*Math.cos(rot)-ey*Math.sin(rot));
        float py=cy+(float)(ex*Math.sin(rot)+ey*Math.cos(rot));

        float base=mode==1?4.25f:3.45f;
        float size=dp(Math.max(1.55f,(base-orbitIdx*.13f)*(.72f+.42f*depth)));
        int alpha=(int)(158+97*depth); if(alpha>255)alpha=255;

        spark.setColor(((int)(48+66*depth)<<24)|0x004bd9ff);
        c.drawCircle(px,py,size*2.55f,spark);

        electron.setColor((alpha<<24)|(electronIdx%2==0?0x00efffff:0x0078e8ff));
        c.drawCircle(px,py,size,electron);

        int trails=mode==1?6:5;
        for(int k=1;k<=trails;k++){
            float back=deg-k*(mode==1?5.2f:4.2f);
            double bt=Math.toRadians(back);
            float bx=(float)Math.cos(bt)*rx;
            float by=(float)Math.sin(bt)*ry;
            float qx=cx+(float)(bx*Math.cos(rot)-by*Math.sin(rot));
            float qy=cy+(float)(bx*Math.sin(rot)+by*Math.cos(rot));
            int al=(int)((105-k*14)*(.55f+.45f*depth));
            if(al<12)al=12;
            spark.setColor((al<<24)|0x0054dfff);
            c.drawCircle(qx,qy,Math.max(dp(.55f),size*(.62f-k*.07f)),spark);
        }
    }

    private void drawHaloNodes(Canvas c,float cx,float cy,float min,float a){
        float rad=min*.315f;
        for(int i=0;i<12;i++){
            float deg=a*(i%2==0?.72f:-.48f)+i*30f;
            float x=cx+(float)Math.cos(Math.toRadians(deg))*rad;
            float y=cy+(float)Math.sin(Math.toRadians(deg))*rad;
            float tw=.5f+.5f*(float)Math.sin(Math.toRadians(phase*2.3f+i*37f));
            int al=(int)(65+115*tw);
            spark.setColor((al<<24)|0x0067e5ff);
            c.drawCircle(x,y,dp(.75f+1.05f*tw),spark);
        }
    }

    private void drawCloud(Canvas c,float cx,float cy,float min,float a){
        for(int i=0;i<cloudA.length;i++){
            float deg=cloudA[i]+a*cloudS[i];
            float rad=min*cloudR[i];
            double t=Math.toRadians(deg);
            float wob=(float)Math.sin(Math.toRadians(phase*1.15f+i*31f))*min*.008f;
            float x=cx+(float)Math.cos(t)*(rad+wob);
            float y=cy+(float)Math.sin(t)*(rad*.74f-wob*.4f);
            float tw=.5f+.5f*(float)Math.sin(Math.toRadians(phase*2.1f+i*47f));
            int al=(int)(48+tw*(mode==1?142:96));
            float sz=dp(.62f+tw*(mode==1?1.65f:1.12f));
            spark.setColor((al<<24)|0x0052cfff);
            c.drawCircle(x,y,sz,spark);
        }
    }

    private void drawNucleus(Canvas c,float cx,float cy,float min,float a){
        glow.setShader(new RadialGradient(cx,cy,min*.078f,
            new int[]{0xffffffff,0xe582efff,0x7a42c7ff,0x00000000},
            new float[]{0f,.16f,.50f,1f},Shader.TileMode.CLAMP));
        c.drawCircle(cx,cy,min*.078f,glow);
        glow.setShader(null);

        electron.setColor(0xffffffff);
        c.drawCircle(cx,cy,dp(4.6f+2.0f*pulse+(mode==1?1.4f:0)),electron);

        for(int i=0;i<8;i++){
            float deg=a*1.92f+i*45f;
            float rr=min*(i%2==0?.078f:.098f);
            float x=cx+(float)Math.cos(Math.toRadians(deg))*rr;
            float y=cy+(float)Math.sin(Math.toRadians(deg))*rr*.58f;
            float d=.5f+.5f*(float)Math.sin(Math.toRadians(deg));
            int al=(int)(165+90*d);
            electron.setColor((al<<24)|(i%2==0?0x00ffffff:0x006fe7ff));
            c.drawCircle(x,y,dp(1.55f+1.15f*d),electron);
        }

        arc.setStrokeWidth(dp(1.0f));
        for(int i=0;i<3;i++){
            float rad=min*(.105f+i*.018f);
            oval.set(cx-rad,cy-rad,cx+rad,cy+rad);
            arc.setColor(((115-i*20)<<24)|0x0079eaff);
            c.drawArc(oval,-a*(1.3f+i*.22f)+i*73f,22f,false,arc);
            c.drawArc(oval,a*(1.1f+i*.18f)+i*101f+180f,16f,false,arc);
        }
    }
}
