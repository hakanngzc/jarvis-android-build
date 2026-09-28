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
    public static final String RENDER_PROFILE = "ELITE_ATOM_V3";

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

    private final float[] cloudA={8,29,51,74,98,124,149,176,203,229,254,278,304,329,348,42,111,189,267,316};
    private final float[] cloudR={.29f,.34f,.38f,.32f,.41f,.36f,.30f,.39f,.33f,.42f,.31f,.37f,.28f,.40f,.35f,.43f,.27f,.365f,.325f,.395f};
    private final float[] cloudS={.54f,-.71f,.91f,-.62f,.77f,-.83f,.67f,-.95f,.58f,-.74f,.88f,-.69f,.81f,-.57f,.93f,-.79f,.63f,-.87f,.72f,-.66f};

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
        animator.setDuration(9000L);
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
        drawCore(c,cx,cy,min,a);

        float r=min*.35f;
        drawOrbit(c,cx,cy,r,      r*.36f,a,        0,0);
        drawOrbit(c,cx,cy,r*.96f, r*.38f,-a*.84f, 56,1);
        drawOrbit(c,cx,cy,r*.92f, r*.34f,a*1.08f,-56,2);
        drawOrbit(c,cx,cy,r*.84f, r*.29f,-a*1.26f,28,3);
        drawOrbit(c,cx,cy,r*.78f, r*.25f,a*1.42f,-30,4);
        drawOrbit(c,cx,cy,r*.70f, r*.22f,-a*1.58f,82,5);

        drawCloud(c,cx,cy,min,a);
        drawNucleus(c,cx,cy,min,a);
    }

    private void drawAura(Canvas c,float cx,float cy,float min,float a){
        float rr=min*(.205f+.018f*pulse+(mode==1?.012f:0));
        int center=mode==1?0xdd88f2ff:(mode==2?0xc86ddfff:0xa85ed8ff);
        glow.setShader(new RadialGradient(cx,cy,rr,
            new int[]{center,0x6046c8ff,0x24347fb9,0x0000070d},
            new float[]{0f,.34f,.68f,1f},Shader.TileMode.CLAMP));
        c.drawCircle(cx,cy,rr,glow);
        glow.setShader(null);

        orbit.setStrokeWidth(dp(.9f));
        for(int i=0;i<4;i++){
            orbit.setColor((42-i*7)<<24|0x003baeff);
            float rad=min*(.235f+i*.053f)+pulse*dp(.8f+i*.2f);
            c.drawCircle(cx,cy,rad,orbit);
        }

        arc.setStrokeWidth(dp(mode==1?1.9f:1.25f));
        for(int i=0;i<3;i++){
            float rad=min*(.27f+i*.058f);
            oval.set(cx-rad,cy-rad,cx+rad,cy+rad);
            int al=mode==1?125:72;
            arc.setColor((al<<24)|0x004bcaff);
            c.drawArc(oval,a*(i%2==0?.55f:-.42f)+i*93f,28f+i*7f,false,arc);
            c.drawArc(oval,a*(i%2==0?.55f:-.42f)+i*93f+184f,16f+i*5f,false,arc);
        }
    }

    private void drawCore(Canvas c,float cx,float cy,float min,float a){
        orbit.setStrokeWidth(dp(1.15f));
        for(int i=0;i<3;i++){
            int al=125-i*25;
            orbit.setColor((al<<24)|0x0047cfff);
            c.drawCircle(cx,cy,min*(.085f+i*.033f)+pulse*dp(.45f),orbit);
        }
        arc.setStrokeWidth(dp(1.8f));
        arc.setColor(mode==1?0xd5bdf8ff:0x957bddff);
        float r=min*.143f; oval.set(cx-r,cy-r,cx+r,cy+r);
        c.drawArc(oval,a*1.2f,72,false,arc);
        c.drawArc(oval,-a*.9f+158,39,false,arc);
    }

    private void drawOrbit(Canvas c,float cx,float cy,float rx,float ry,float spin,float baseTilt,int idx){
        float precess=(float)Math.sin(Math.toRadians(phase*.22f+idx*63f))*7f;
        float tilt=baseTilt+precess;

        int backAlpha=mode==1?80:52;
        orbit.setColor((backAlpha<<24)|0x0038aeea);
        orbit.setStrokeWidth(dp(idx<2?1.15f:.85f));
        c.save();
        c.rotate(tilt,cx,cy);
        oval.set(cx-rx,cy-ry,cx+rx,cy+ry);
        c.drawOval(oval,orbit);

        int frontAlpha=mode==1?205:(mode==2?172:145);
        frontOrbit.setColor((frontAlpha<<24)|0x0052d9ff);
        frontOrbit.setStrokeWidth(dp(idx<2?1.85f:1.25f));
        float start=(spin*.35f+idx*37f)%360f;
        c.drawArc(oval,start,120,false,frontOrbit);
        c.drawArc(oval,start+180,52,false,frontOrbit);
        c.restore();

        int count=idx<3?3:2;
        for(int e=0;e<count;e++){
            float deg=spin+e*(360f/count)+idx*29f;
            drawElectron(c,cx,cy,rx,ry,deg,tilt,idx,e);
        }
    }

    private void drawElectron(Canvas c,float cx,float cy,float rx,float ry,float deg,float tilt,int orbitIdx,int electronIdx){
        double t=Math.toRadians(deg);
        float depth=.5f+.5f*(float)Math.sin(t);
        float[] p=point(cx,cy,rx,ry,deg,tilt);

        float base=mode==1?4.15f:3.35f;
        float size=dp((base-orbitIdx*.15f)*(.72f+.42f*depth));
        int alpha=(int)(150+100*depth); if(alpha>255)alpha=255;

        spark.setColor(((int)(40+60*depth)<<24)|0x004bd9ff);
        c.drawCircle(p[0],p[1],size*2.4f,spark);

        electron.setColor((alpha<<24)|(electronIdx%2==0?0x00efffff:0x0078e8ff));
        c.drawCircle(p[0],p[1],size,electron);

        int trails=mode==1?4:3;
        for(int k=1;k<=trails;k++){
            float back=deg-k*(mode==1?4.8f:3.5f);
            float[] q=point(cx,cy,rx,ry,back,tilt);
            int al=(int)((90-k*16)*(.55f+.45f*depth));
            if(al<14)al=14;
            spark.setColor((al<<24)|0x0054dfff);
            c.drawCircle(q[0],q[1],Math.max(dp(.7f),size*(.55f-k*.08f)),spark);
        }
    }

    private float[] point(float cx,float cy,float rx,float ry,float deg,float tilt){
        double t=Math.toRadians(deg);
        float x=(float)Math.cos(t)*rx;
        float y=(float)Math.sin(t)*ry;
        double r=Math.toRadians(tilt);
        return new float[]{
            cx+(float)(x*Math.cos(r)-y*Math.sin(r)),
            cy+(float)(x*Math.sin(r)+y*Math.cos(r))
        };
    }

    private void drawCloud(Canvas c,float cx,float cy,float min,float a){
        for(int i=0;i<cloudA.length;i++){
            float deg=cloudA[i]+a*cloudS[i];
            float rad=min*cloudR[i];
            double t=Math.toRadians(deg);
            float wob=(float)Math.sin(Math.toRadians(phase*.9f+i*31f))*min*.007f;
            float x=cx+(float)Math.cos(t)*(rad+wob);
            float y=cy+(float)Math.sin(t)*(rad*.74f-wob*.4f);
            float tw=.5f+.5f*(float)Math.sin(Math.toRadians(phase*1.7f+i*47f));
            int al=(int)(45+tw*(mode==1?125:80));
            float sz=dp(.7f+tw*(mode==1?1.55f:1.0f));
            spark.setColor((al<<24)|0x0052cfff);
            c.drawCircle(x,y,sz,spark);
        }
    }

    private void drawNucleus(Canvas c,float cx,float cy,float min,float a){
        glow.setShader(new RadialGradient(cx,cy,min*.07f,
            new int[]{0xfff4feff,0xcc66e8ff,0x6639baff,0x00000000},
            new float[]{0f,.18f,.52f,1f},Shader.TileMode.CLAMP));
        c.drawCircle(cx,cy,min*.07f,glow);
        glow.setShader(null);

        electron.setColor(0xffffffff);
        c.drawCircle(cx,cy,dp(4.2f+1.8f*pulse+(mode==1?1.3f:0)),electron);

        for(int i=0;i<4;i++){
            float deg=a*1.75f+i*90f;
            float rr=min*.074f;
            float x=cx+(float)Math.cos(Math.toRadians(deg))*rr;
            float y=cy+(float)Math.sin(Math.toRadians(deg))*rr*.54f;
            float d=.5f+.5f*(float)Math.sin(Math.toRadians(deg));
            int al=(int)(160+95*d);
            electron.setColor((al<<24)|(i%2==0?0x00ffffff:0x006fe7ff));
            c.drawCircle(x,y,dp(1.8f+1.0f*d),electron);
        }
    }
}
