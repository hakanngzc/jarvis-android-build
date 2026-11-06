package com.glassos.launcher;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.RadialGradient;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Shader;
import android.graphics.drawable.GradientDrawable;
import android.view.View;
import android.widget.FrameLayout;

/** GlassOS wallpaper and a CPU-preblurred, position-aware glass material.
 * All wallpaper work is cached: no per-frame bitmap filtering, no live GPU blur.
 */
final class LiquidArt {
    static final int WHITE=0xfff5f9ff;
    static final int MUTED=0xffc1cde3;
    static final int BLUE=0xff9ad7ff;
    private static Bitmap wallpaper;
    private static Bitmap frosted;
    private static int width,height,mode=-1;
    private static final Object LOCK=new Object();
    static int dp(Context c,float n){return (int)(n*c.getResources().getDisplayMetrics().density+.5f);}

    static void invalidate(){synchronized(LOCK){if(wallpaper!=null)wallpaper.recycle();if(frosted!=null)frosted.recycle();wallpaper=null;frosted=null;width=0;height=0;mode=-1;}}
    static void prepare(Context c,int w,int h){
        if(w<1||h<1)return;
        SharedPreferences p=c.getSharedPreferences("glassos_prefs",0);
        int style=p.getInt("wallpaper",0);
        synchronized(LOCK){
            if(wallpaper!=null && width==w && height==h && mode==style)return;
            if(wallpaper!=null)wallpaper.recycle();
            if(frosted!=null)frosted.recycle();
            width=w;height=h;mode=style;
            Bitmap b=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
            Canvas ca=new Canvas(b);
            Paint pen=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
            int[] colors=style==1?
              new int[]{0xff07162d,0xff133f68,0xff063452,0xff050d1c}:
              style==2?new int[]{0xff080c18,0xff26223b,0xff12192b,0xff060b14}:
              new int[]{0xff060c1d,0xff122e55,0xff071c37,0xff040a17};
            pen.setShader(new LinearGradient(0,0,w,h,colors,null,Shader.TileMode.CLAMP));
            ca.drawRect(0,0,w,h,pen);
            glow(ca,pen,w*.88f,h*.27f,w*.92f,style==2?0x997f69d9:0xa54b86f4);
            glow(ca,pen,w*.07f,h*.79f,w*.98f,style==1?0x9b15b8ba:0x9a1d6bd7);
            glow(ca,pen,w*.30f,h*.52f,w*.78f,style==2?0x6d965eb8:0x6c4067bd);
            glow(ca,pen,w*.94f,h*.94f,w*.70f,0x9b173e81);
            pen.setShader(null);
            pen.setStyle(Paint.Style.STROKE);
            pen.setStrokeCap(Paint.Cap.ROUND);
            for(int i=0;i<4;i++){
                Path arc=new Path();
                float off=i*w*.08f;
                arc.moveTo(w*.33f+off,-h*.10f);
                arc.cubicTo(w*.94f+off,h*.16f,w*.35f+off,h*.46f,w*1.14f+off,h*.64f);
                pen.setStrokeWidth(w*(.075f+i*.018f));
                pen.setColor(i%2==0?0x0f9ad7ff:0x0b7caaff);
                ca.drawPath(arc,pen);
            }
            pen.setStyle(Paint.Style.FILL);
            // A subtly lit edge and gentle vignette gives dimensionality.
            pen.setShader(new LinearGradient(0,0,w*.68f,h,
                new int[]{0x33000000,0x00000000,0x26000000},null,Shader.TileMode.CLAMP));
            ca.drawRect(0,0,w,h,pen);
            pen.setShader(null);
            wallpaper=b;
            int sw=Math.max(36,w/7),sh=Math.max(80,h/7);
            Bitmap tiny=Bitmap.createScaledBitmap(b,sw,sh,true);
            frosted=softBlur(tiny,7);
            if(frosted!=tiny)tiny.recycle();
        }
    }
    private static void glow(Canvas canvas,Paint pen,float cx,float cy,float radius,int inner){
        pen.setShader(new RadialGradient(cx,cy,Math.max(1,radius),
            new int[]{inner,(inner&0x00ffffff)|0x26000000,0x00000000},
            new float[]{0,.46f,1},Shader.TileMode.CLAMP));
        canvas.drawRect(0,0,canvas.getWidth(),canvas.getHeight(),pen);
    }
    private static Bitmap softBlur(Bitmap original,int radius){
        int w=original.getWidth(),h=original.getHeight();
        int[] a=new int[w*h],tmp=new int[w*h],out=new int[w*h];
        original.getPixels(a,0,w,0,0,w,h);
        for(int y=0;y<h;y++){
            for(int x=0;x<w;x++){
                int rs=0,gs=0,bs=0,n=0;
                for(int i=Math.max(0,x-radius);i<=Math.min(w-1,x+radius);i++){
                    int v=a[y*w+i];rs+=(v>>16)&255;gs+=(v>>8)&255;bs+=v&255;n++;
                }
                tmp[y*w+x]=0xff000000|((rs/n)<<16)|((gs/n)<<8)|(bs/n);
            }
        }
        for(int x=0;x<w;x++){
            for(int y=0;y<h;y++){
                int rs=0,gs=0,bs=0,n=0;
                for(int i=Math.max(0,y-radius);i<=Math.min(h-1,y+radius);i++){
                    int v=tmp[i*w+x];rs+=(v>>16)&255;gs+=(v>>8)&255;bs+=v&255;n++;
                }
                out[y*w+x]=0xff000000|((rs/n)<<16)|((gs/n)<<8)|(bs/n);
            }
        }
        Bitmap blurred=Bitmap.createBitmap(w,h,Bitmap.Config.ARGB_8888);
        blurred.setPixels(out,0,w,0,0,w,h);
        return blurred;
    }

    static final class Wallpaper extends View {
        private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
        Wallpaper(Context c){super(c);}
        @Override protected void onDraw(Canvas c){
            int sw=getResources().getDisplayMetrics().widthPixels;
            int sh=getResources().getDisplayMetrics().heightPixels;
            prepare(getContext(),Math.max(sw,getWidth()),Math.max(sh,getHeight()));
            Bitmap b=wallpaper;
            if(b!=null&&!b.isRecycled())c.drawBitmap(b,null,new Rect(0,0,getWidth(),getHeight()),paint);
        }
    }

    static final class Glass extends FrameLayout {
        private final Paint pen=new Paint(Paint.ANTI_ALIAS_FLAG|Paint.FILTER_BITMAP_FLAG);
        private final Path clip=new Path();
        private final RectF r=new RectF();
        private final float corner;
        private final boolean strong;
        private final int[] loc=new int[2];
        Glass(Context c,int cornerDp,boolean strongMaterial){
            super(c);corner=dp(c,cornerDp);strong=strongMaterial;
            setWillNotDraw(false);
        }
        @Override protected void onDraw(Canvas c){
            float w=getWidth(),h=getHeight();
            if(w<1||h<1)return;
            r.set(0,0,w,h);clip.reset();clip.addRoundRect(r,corner,corner,Path.Direction.CW);
            int save=c.save();
            c.clipPath(clip);
            Bitmap b=frosted;
            if(b!=null&&!b.isRecycled()&&width>0&&height>0){
                getLocationOnScreen(loc);
                Rect from=new Rect((int)(loc[0]*(float)b.getWidth()/width),
                    (int)(loc[1]*(float)b.getHeight()/height),
                    (int)((loc[0]+w)*(float)b.getWidth()/width),
                    (int)((loc[1]+h)*(float)b.getHeight()/height));
                from.intersect(0,0,b.getWidth(),b.getHeight());
                if(!from.isEmpty())c.drawBitmap(b,from,r,pen);
            }
            int glass=getContext().getSharedPreferences("glassos_prefs",0).getInt("glass",52);
            int alpha=(int)(40+(glass/100f)*135);
            pen.setShader(null);pen.setStyle(Paint.Style.FILL);
            pen.setColor(Color.argb(strong?Math.min(218,alpha+35):alpha,12,27,50));
            c.drawRoundRect(r,corner,corner,pen);
            pen.setShader(new LinearGradient(0,0,w*.7f,h,
                new int[]{0x2cffffff,0x0aebf8ff,0x03ffffff},null,Shader.TileMode.CLAMP));
            c.drawRoundRect(r,corner,corner,pen);
            pen.setShader(null);
            c.restoreToCount(save);
            pen.setStyle(Paint.Style.STROKE);
            pen.setStrokeWidth(dp(getContext(),1));
            pen.setColor(strong?0x88d6eaff:0x66cae6ff);
            c.drawRoundRect(dp(getContext(),.5f),dp(getContext(),.5f),
                w-dp(getContext(),.5f),h-dp(getContext(),.5f),corner,corner,pen);
            pen.setColor(0x44ffffff);
            pen.setStrokeWidth(dp(getContext(),.8f));
            c.drawArc(dp(getContext(),2),dp(getContext(),2),w-dp(getContext(),2),
                Math.min(h*.74f,dp(getContext(),70)),197,130,false,pen);
            pen.setStyle(Paint.Style.FILL);
        }
    }

    static GradientDrawable capsule(Context c,boolean accent){
        GradientDrawable d=new GradientDrawable(GradientDrawable.Orientation.TL_BR,
            accent?new int[]{0xffa8e1ff,0xff72adf0}:new int[]{0x556a90bd,0x44324d75});
        d.setCornerRadius(dp(c,22));
        if(!accent)d.setStroke(dp(c,1),0x99bfdcf9);
        return d;
    }
    private LiquidArt(){}
}
