package com.hakan.jarvis;

import android.animation.ValueAnimator;
import android.content.Context;
import android.graphics.Canvas;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RadialGradient;
import android.graphics.Shader;
import android.view.View;
import android.view.animation.LinearInterpolator;

public final class JarvisEliteBackdropView extends View {
    public static final String PROFILE = "ELITE_BACKDROP_V1";
    private final Paint p = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint grid = new Paint(Paint.ANTI_ALIAS_FLAG);
    private final Paint node = new Paint(Paint.ANTI_ALIAS_FLAG);
    private float phase = 0f;
    private ValueAnimator animator;

    private final float[] px={.08f,.16f,.24f,.33f,.43f,.52f,.62f,.71f,.81f,.90f,.13f,.28f,.47f,.67f,.86f,.20f,.39f,.58f,.77f,.94f};
    private final float[] py={.11f,.27f,.18f,.41f,.09f,.31f,.22f,.38f,.15f,.29f,.61f,.73f,.57f,.69f,.53f,.88f,.79f,.91f,.82f,.74f};

    public JarvisEliteBackdropView(Context c){
        super(c);
        setLayerType(View.LAYER_TYPE_HARDWARE,null);
        grid.setStrokeWidth(dp(.7f));
        start();
    }
    private float dp(float v){return v*getResources().getDisplayMetrics().density;}
    private void start(){
        if(animator!=null)animator.cancel();
        animator=ValueAnimator.ofFloat(0f,1f);
        animator.setDuration(16000L);
        animator.setRepeatCount(ValueAnimator.INFINITE);
        animator.setInterpolator(new LinearInterpolator());
        animator.addUpdateListener(a->{phase=(Float)a.getAnimatedValue();invalidate();});
        animator.start();
    }
    @Override protected void onDetachedFromWindow(){super.onDetachedFromWindow();if(animator!=null)animator.cancel();}
    @Override protected void onAttachedToWindow(){super.onAttachedToWindow();if(animator==null||!animator.isRunning())start();}

    @Override protected void onDraw(Canvas c){
        super.onDraw(c);
        float w=getWidth(),h=getHeight();
        if(w<=0||h<=0)return;

        p.setShader(new LinearGradient(0,0,0,h,new int[]{0xff020812,0xff03101b,0xff01060c},null,Shader.TileMode.CLAMP));
        c.drawRect(0,0,w,h,p);

        p.setShader(new RadialGradient(w*.52f,h*.38f,Math.max(w,h)*.56f,
            new int[]{0x33259fe8,0x15105a8f,0x0000060c},
            new float[]{0f,.45f,1f},Shader.TileMode.CLAMP));
        c.drawCircle(w*.52f,h*.38f,Math.max(w,h)*.56f,p);
        p.setShader(null);

        grid.setColor(0x121f8ac0);
        float step=dp(46);
        float drift=(phase*step);
        for(float x=-step+drift;x<w+step;x+=step)c.drawLine(x,0,x,h,grid);
        for(float y=-step+drift*.35f;y<h+step;y+=step)c.drawLine(0,y,w,y,grid);

        float scan=(phase*1.35f%1f)*h;
        p.setShader(new LinearGradient(0,scan-dp(34),0,scan+dp(34),
            new int[]{0x001ea9ff,0x171ea9ff,0x001ea9ff},null,Shader.TileMode.CLAMP));
        c.drawRect(0,scan-dp(34),w,scan+dp(34),p);
        p.setShader(null);

        for(int i=0;i<px.length;i++){
            float dy=(float)Math.sin((phase*6.283185f)+(i*.63f))*dp(8+i%4);
            float x=px[i]*w;
            float y=py[i]*h+dy;
            float tw=.45f+.55f*(float)Math.sin(phase*12.566f+i*1.17f);
            int a=(int)(35+55*Math.max(0,tw));
            node.setColor((a<<24)|0x004fd6ff);
            c.drawCircle(x,y,dp(1.1f+(i%3)*.45f),node);
        }

        p.setStyle(Paint.Style.STROKE);
        p.setStrokeWidth(dp(1));
        p.setColor(0x1737b7ff);
        float r=Math.min(w,h)*.42f;
        c.drawCircle(w*.5f,h*.39f,r,p);
        p.setColor(0x0f37b7ff);
        c.drawCircle(w*.5f,h*.39f,r*1.22f,p);
        p.setStyle(Paint.Style.FILL);
    }
}
